"""
LangGraph IRRBB workflow: market + balance sheet -> EVE -> Basel gate -> HITL -> report.

This is the use case LangGraph is for here (vs a single LLM call):
- parallel data nodes
- a real conditional edge on the 15% Basel outlier test
- interrupt_before so a risk manager can approve before the narrative is written
- checkpointed state so Streamlit can pause and resume the same thread
"""

import os
import sys
from typing import TypedDict

import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from models.enhanced_eve_calculator import EnhancedEVECalculator  # noqa: E402
from utils.market_data import FederalReserveData  # noqa: E402

load_dotenv()

BASEL_OUTLIER_THRESHOLD_PCT = 15.0
BASEL_WATCH_THRESHOLD_PCT = 10.0


def _to_native(records_or_dict):
    """Cast numpy scalars so LangGraph checkpoints can serialize state."""
    if isinstance(records_or_dict, list):
        return [_to_native(r) for r in records_or_dict]
    if isinstance(records_or_dict, dict):
        return {k: _to_native(v) for k, v in records_or_dict.items()}
    if hasattr(records_or_dict, "item"):
        return records_or_dict.item()
    return records_or_dict


class IRRBBState(TypedDict, total=False):
    query: str
    use_real_data: bool
    market_context: dict
    balance_sheet: list
    stats: dict
    sensitivity: list
    base_eve: float
    worst_scenario: str
    worst_change_pct: float
    compliance_status: str
    compliance_action: str
    needs_review: bool
    review_notes: str
    report: str


def fetch_market_context(state: IRRBBState) -> dict:
    if state.get("market_context"):
        return {}

    use_real = state.get("use_real_data", True)
    if use_real:
        try:
            fed = FederalReserveData()
            rate_10y = float(fed.get_treasury_rate("10Y"))
            change_30d = float(fed.get_rate_change("10Y", 30))
            source = "Federal Reserve (10Y Treasury)"
        except Exception as exc:
            rate_10y = 0.045
            change_30d = 0.0
            source = f"Assumed rate (FRED unavailable: {exc})"
    else:
        rate_10y = 0.045
        change_30d = 0.0
        source = "Assumed rate (demo mode)"

    vol = abs(change_30d)
    risk_level = "HIGH" if vol > 50 else "MODERATE" if vol > 25 else "LOW"
    return {
        "market_context": {
            "rate_10y": rate_10y,
            "change_30d_bp": change_30d,
            "volatility": risk_level,
            "source": source,
        }
    }


def fetch_balance_sheet(state: IRRBBState) -> dict:
    if state.get("balance_sheet") and state.get("stats"):
        return {}

    use_real = state.get("use_real_data", True)
    calc = EnhancedEVECalculator(use_real_data=use_real)
    bs = calc.create_sample_balance_sheet()
    stats = calc.get_summary_stats(bs)
    return {
        "balance_sheet": _to_native(bs.to_dict("records")),
        "stats": _to_native(stats),
    }


def run_sensitivity(state: IRRBBState) -> dict:
    if state.get("sensitivity") and "base_eve" in state:
        return {}

    use_real = state.get("use_real_data", True)
    calc = EnhancedEVECalculator(use_real_data=use_real)
    results, _scenario_info = calc.run_sensitivity_analysis()

    base_eve = results.loc[results["shock_bp"] == 0, "eve"].iloc[0]
    worst = results.loc[results["change_$"].idxmin()]
    return {
        "sensitivity": _to_native(results.to_dict("records")),
        "base_eve": float(base_eve),
        "worst_scenario": str(worst["scenario"]),
        "worst_change_pct": float(worst["change_%"]),
    }


def assess_compliance(state: IRRBBState) -> dict:
    change_pct = abs(float(state["worst_change_pct"]))

    if change_pct > BASEL_OUTLIER_THRESHOLD_PCT:
        status = "EXCEEDS THRESHOLD - Supervisory outlier"
        action = "Immediate remediation plan required"
        needs_review = True
    elif change_pct > BASEL_WATCH_THRESHOLD_PCT:
        status = "APPROACHING THRESHOLD - Heightened oversight"
        action = "Develop contingency hedging strategy"
        needs_review = True
    else:
        status = "WITHIN LIMITS - Normal monitoring"
        action = "Continue quarterly reviews"
        needs_review = False

    return {
        "compliance_status": status,
        "compliance_action": action,
        "needs_review": needs_review,
    }


def route_after_compliance(state: IRRBBState) -> str:
    return "human_review" if state.get("needs_review") else "analyst_report"


def human_review(state: IRRBBState) -> dict:
    """Pass-through. The graph interrupts *before* this node so a person can sign off."""
    return {}


def analyst_report(state: IRRBBState) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the .env file")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    stats = state["stats"]
    market = state.get("market_context") or {}
    notes = state.get("review_notes") or "None"
    sensitivity = pd.DataFrame(state.get("sensitivity") or [])

    prompt = f"""You are an expert IRRBB risk analyst. Write a concise markdown report
(executive summary, key numbers, Basel view, 3 actions). Use only these facts.

Market: 10Y {market.get('rate_10y', 0)*100:.2f}%, 30d change {market.get('change_30d_bp', 0):+.0f}bp,
volatility {market.get('volatility', 'n/a')}, source {market.get('source', 'n/a')}

Balance sheet: Assets ${stats['total_assets']:,.0f}, Liabilities ${stats['total_liabilities']:,.0f},
Equity ${stats['equity']:,.0f}, Leverage {stats['leverage_ratio']:.2f}x

Sensitivity:
{sensitivity.to_string(index=False) if not sensitivity.empty else 'n/a'}

Base EVE: ${state['base_eve']:,.2f}
Worst-case: {state['worst_scenario']} ({state['worst_change_pct']:+.2f}%)
Compliance: {state['compliance_status']}
Required action: {state['compliance_action']}
Reviewer notes: {notes}

Original question: {state.get('query', 'Provide a general risk assessment.')}"""

    response = llm.invoke(
        [
            SystemMessage(content="You are a precise, regulation-literate financial risk analyst."),
            HumanMessage(content=prompt),
        ]
    )
    return {"report": response.content}


def build_graph(interrupt_for_review: bool = True):
    graph = StateGraph(IRRBBState)

    graph.add_node("fetch_market_context", fetch_market_context)
    graph.add_node("fetch_balance_sheet", fetch_balance_sheet)
    graph.add_node("run_sensitivity", run_sensitivity)
    graph.add_node("assess_compliance", assess_compliance)
    graph.add_node("human_review", human_review)
    graph.add_node("analyst_report", analyst_report)

    graph.add_edge(START, "fetch_market_context")
    graph.add_edge(START, "fetch_balance_sheet")
    graph.add_edge("fetch_market_context", "run_sensitivity")
    graph.add_edge("fetch_balance_sheet", "run_sensitivity")
    graph.add_edge("run_sensitivity", "assess_compliance")
    graph.add_conditional_edges(
        "assess_compliance",
        route_after_compliance,
        {"human_review": "human_review", "analyst_report": "analyst_report"},
    )
    graph.add_edge("human_review", "analyst_report")
    graph.add_edge("analyst_report", END)

    checkpointer = InMemorySaver()
    interrupt_before = ["human_review"] if interrupt_for_review else []
    return graph.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)


def initial_state_from_dashboard(
    results: pd.DataFrame,
    bs: pd.DataFrame,
    stats: dict,
    use_real_data: bool,
    query: str = "Summarize current IRRBB EVE risk and Basel compliance.",
) -> dict:
    """Seed the graph with numbers the dashboard already computed."""
    base_eve = float(results.loc[results["shock_bp"] == 0, "eve"].iloc[0])
    worst = results.loc[results["change_$"].idxmin()]
    return {
        "query": query,
        "use_real_data": use_real_data,
        "balance_sheet": _to_native(bs.to_dict("records")),
        "stats": _to_native(stats),
        "sensitivity": _to_native(results.to_dict("records")),
        "base_eve": base_eve,
        "worst_scenario": str(worst["scenario"]),
        "worst_change_pct": float(worst["change_%"]),
    }


def is_interrupted(app, config: dict) -> bool:
    snapshot = app.get_state(config)
    return bool(snapshot.next)


def run_demo():
    app = build_graph(interrupt_for_review=True)
    config = {"configurable": {"thread_id": "demo-run-1"}}
    query = "What is our EVE sensitivity, and are we compliant with Basel IRRBB standards?"

    print("=" * 80)
    print("LANGGRAPH IRRBB ORCHESTRATION")
    print("=" * 80)

    result = app.invoke({"query": query, "use_real_data": True}, config=config)

    if is_interrupted(app, config):
        print("\nPaused for human review before the analyst report.")
        print(f"   Compliance: {result['compliance_status']}")
        print(f"   Worst case: {result['worst_scenario']} ({result['worst_change_pct']:+.2f}%)")
        notes = input("\nOptional review notes (Enter to approve): ").strip()
        if notes:
            app.update_state(config, {"review_notes": notes})
        result = app.invoke(None, config=config)

    print("\nFINAL REPORT")
    print("-" * 80)
    print(result["report"])
    print("-" * 80)
    print(f"\nCompliance status: {result['compliance_status']}")


if __name__ == "__main__":
    run_demo()
