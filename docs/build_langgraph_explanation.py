"""Generate the LangGraph IRRBB explanation Word document."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


def set_run_font(run, size=11, bold=False, color=None):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color


def add_heading_styled(doc, text, level):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    return p


def add_body(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, 11)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.space_before = Pt(0)
    return p


def add_bullet(doc, text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        r1 = p.add_run(bold_prefix)
        set_run_font(r1, 11, bold=True)
        r2 = p.add_run(text)
        set_run_font(r2, 11)
    else:
        r = p.add_run(text)
        set_run_font(r, 11)
    return p


def main():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("LangGraph in the IRRBB Agent System")
    set_run_font(run, 22, bold=True, color=RGBColor(0x1F, 0x4E, 0x79))

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(
        "How the workflow is designed, why it is used, and how it runs in the dashboard"
    )
    set_run_font(run, 12, color=RGBColor(0x5B, 0x5B, 0x5B))

    add_heading_styled(doc, "1. What this project is doing", 1)
    add_body(
        doc,
        "This project is an Interest Rate Risk in the Banking Book (IRRBB) prototype. "
        "It measures how a sample bank balance sheet changes in value when market rates "
        "move. The core metric is Economic Value of Equity (EVE): the present value of "
        "assets minus the present value of liabilities. Regulators care about EVE because "
        "a large decline under a rate shock can mark the bank as a supervisory outlier.",
    )
    add_body(
        doc,
        "The Streamlit dashboard already computes EVE scenarios, plots them, and checks "
        "the Basel-style 15 percent outlier test. LangGraph is used only for the AI "
        "workflow on top of those numbers: routing, pausing for a person, then writing "
        "the narrative report.",
    )

    add_heading_styled(doc, "2. Why LangGraph, not a single LLM call", 1)
    add_body(
        doc,
        "A single prompt to GPT can write a nice memo, but it cannot reliably do the "
        "control-flow a risk process needs. LangGraph is used here because IRRBB analysis "
        "is a pipeline with rules, not a chat.",
    )
    add_bullet(
        doc,
        " Market data from the Federal Reserve and the balance sheet can be gathered at the same time.",
        "Parallel work.",
    )
    add_bullet(
        doc,
        " EVE math is deterministic. It should not be invented by the model.",
        "Deterministic steps.",
    )
    add_bullet(
        doc,
        " If the worst EVE move is inside limits, the report can be written immediately. If it is a watch item or an outlier, a person should sign off first.",
        "A real branch.",
    )
    add_bullet(
        doc,
        " The graph can stop, keep its state, and resume after a risk manager adds notes. A normal LangChain chain cannot do that cleanly.",
        "Human-in-the-loop.",
    )

    add_heading_styled(doc, "3. The use case in one sentence", 1)
    add_body(
        doc,
        "Run a supervised IRRBB workflow: collect market and book data, compute EVE "
        "sensitivity, apply Basel thresholds, pause for human review when risk is elevated, "
        "then generate an analyst report that uses only the facts already in state.",
    )

    add_heading_styled(doc, "4. How the graph is structured", 1)
    add_body(
        doc,
        "The graph lives in agents/langgraph_orchestrator.py. Shared memory is a typed "
        "state object (IRRBBState). Each node reads that state and returns only the fields "
        "it updates. Values are stored as plain Python types (lists of dictionaries, floats, "
        "strings) so LangGraph can checkpoint them. Pandas DataFrames are converted at the "
        "boundary because the checkpointer cannot serialize numpy types.",
    )

    add_heading_styled(doc, "4.1 Nodes", 2)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "Node"
    hdr[1].text = "What it does"
    rows = [
        (
            "fetch_market_context",
            "Loads the 10-year Treasury yield and 30-day change from FRED when live data is on. Otherwise uses a demo rate. Labels volatility as HIGH / MODERATE / LOW.",
        ),
        (
            "fetch_balance_sheet",
            "Loads the sample banking book and summary stats (assets, liabilities, equity, leverage, weighted average maturity). Skips work if the dashboard already passed this data in.",
        ),
        (
            "run_sensitivity",
            "Runs the EVE shock ladder with EnhancedEVECalculator. Records base EVE, the worst scenario name, and the worst percentage change. Also skips if the dashboard already supplied results.",
        ),
        (
            "assess_compliance",
            "Applies the Basel-style gate on the absolute worst EVE change: above 15 percent is a supervisory outlier; above 10 percent is a watch item; otherwise within limits. Sets needs_review True for outlier and watch.",
        ),
        (
            "human_review",
            "A placeholder node. The compiled graph is configured to interrupt before this node, so a person can approve and optionally add review notes.",
        ),
        (
            "analyst_report",
            "Calls GPT-4o-mini with the numbers already in state and writes a short markdown memo. It is instructed not to invent figures.",
        ),
    ]
    for name, desc in rows:
        cells = table.add_row().cells
        cells[0].text = name
        cells[1].text = desc

    add_heading_styled(doc, "4.2 Edges and routing", 2)
    add_body(
        doc,
        "START fans out to fetch_market_context and fetch_balance_sheet at the same time. "
        "Both of those nodes feed run_sensitivity, which therefore waits until both "
        "parents finish. Sensitivity then goes to assess_compliance.",
    )
    add_body(
        doc,
        "From assess_compliance a conditional edge named route_after_compliance decides "
        "the next step: human_review if needs_review is True, otherwise analyst_report. "
        "After human review, the graph always continues to analyst_report, then END.",
    )

    add_heading_styled(doc, "4.3 Flow in plain language", 2)
    add_body(
        doc,
        "Start → (market and balance sheet in parallel) → EVE sensitivity → Basel gate → "
        "either go straight to the AI report, or pause for a person, then write the report → End.",
    )

    add_heading_styled(doc, "5. Thresholds used in this prototype", 1)
    add_body(
        doc,
        "These are teaching thresholds aligned with the common Basel IRRBB EVE outlier "
        "idea (a large EVE decline relative to capital). They are not a full BCBS 368 "
        "implementation (no currency-specific shocks, no NII, no behavioral options).",
    )
    add_bullet(doc, " Worst |EVE change| greater than 15 percent → EXCEEDS THRESHOLD, needs_review = True.", "Outlier.")
    add_bullet(doc, " Worst |EVE change| greater than 10 percent → APPROACHING THRESHOLD, needs_review = True.", "Watch.")
    add_bullet(doc, " Otherwise → WITHIN LIMITS, needs_review = False, report is generated immediately.", "Normal.")

    add_heading_styled(doc, "6. How this is integrated in the web dashboard", 1)
    add_body(
        doc,
        "dashboard.py still computes charts and Basel metrics itself. The LangGraph "
        "section does not re-invent those numbers. It seeds the graph with "
        "initial_state_from_dashboard(results, bs, stats, use_real_data) so the AI path "
        "stays consistent with what the user already sees on the page.",
    )
    add_bullet(
        doc,
        " The compiled graph is cached with @st.cache_resource so the in-memory checkpointer survives Streamlit reruns.",
        "Cached graph.",
    )
    add_bullet(
        doc,
        " Each analysis run gets a thread_id. When the EVE numbers change, a new thread starts.",
        "Session thread.",
    )
    add_bullet(
        doc,
        " idle: invoke the graph. If get_state(...).next is set, the graph is paused before human_review (phase = review). Otherwise the report is already done.",
        "Phase idle.",
    )
    add_bullet(
        doc,
        " The page shows worst scenario, worst EVE change, and compliance. The user may type reviewer notes and click Approve and generate report. That updates state and invokes the graph with None to resume.",
        "Phase review.",
    )
    add_bullet(
        doc,
        " The markdown report from analyst_report is rendered on the page.",
        "Phase done.",
    )
    add_body(
        doc,
        "With the sample balance sheet, EVE usually fails the 15 percent test, so the "
        "review panel is the path you will see most often. That is intentional: it "
        "demonstrates the human checkpoint.",
    )

    add_heading_styled(doc, "7. How to run it", 1)
    add_heading_styled(doc, "7.1 Dashboard", 2)
    add_body(doc, "From the project folder, with the virtual environment active:")
    add_body(doc, "streamlit run dashboard.py")
    add_body(
        doc,
        "Open the local URL (usually http://localhost:8501). Keep Show AI Analysis on. "
        "When the graph pauses, add optional notes and approve. OPENAI_API_KEY must be "
        "set in the .env file for the report node. FRED_API_KEY is used for live Treasury data.",
    )
    add_heading_styled(doc, "7.2 Command-line demo", 2)
    add_body(doc, "python agents/langgraph_orchestrator.py")
    add_body(
        doc,
        "The CLI version uses the same graph. If it pauses, press Enter (or type notes) "
        "to resume and print the final report.",
    )

    add_heading_styled(doc, "8. What LangGraph is not doing in this prototype", 1)
    add_bullet(doc, " It does not replace EnhancedEVECalculator or the Plotly charts.")
    add_bullet(doc, " It does not implement a full multi-currency Basel IRRBB standardized framework.")
    add_bullet(doc, " The checkpointer is InMemorySaver, so pauses do not survive a full process restart. A production bank would swap in SQLite or Postgres.")
    add_bullet(doc, " The sample book is synthetic. Live Fed rates change the discounting, not the product inventory.")

    add_heading_styled(doc, "9. Files to look at", 1)
    add_bullet(doc, " agents/langgraph_orchestrator.py — graph definition, nodes, routing, CLI demo.")
    add_bullet(doc, " dashboard.py — Streamlit UI, human-review pause/resume, report display.")
    add_bullet(doc, " models/enhanced_eve_calculator.py — EVE math and shock scenarios.")
    add_bullet(doc, " utils/market_data.py — Federal Reserve (FRED) market inputs.")
    add_bullet(doc, " agents/financial_analyst_agent.py — earlier one-shot LLM report; the dashboard AI section now uses LangGraph instead.")

    add_heading_styled(doc, "10. Short takeaway", 1)
    add_body(
        doc,
        "LangGraph is the orchestration layer for a regulated-style IRRBB process: "
        "compute first, branch on policy, stop for a human when the bank looks like a "
        "watch or outlier, then let the language model write the memo from facts that "
        "are already in the graph state.",
    )

    out = Path(__file__).resolve().parent / "LangGraph_IRRBB_Workflow.docx"
    doc.save(out)
    print(out)


if __name__ == "__main__":
    main()
