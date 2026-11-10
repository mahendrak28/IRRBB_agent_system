"""
Financial analyst agent for IRRBB EVE dashboard insights.
"""

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv()


class FinancialAnalystAgent:
    """Generate a narrative IRRBB report from EVE sensitivity results."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in the .env file")

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            api_key=api_key,
        )

    def analyze_eve_results(self, results, bs, stats) -> str:
        """
        Produce markdown analysis for dashboard EVE results.

        Args:
            results: DataFrame with scenario, shock_bp, eve, change_$, change_%
            bs: Balance sheet DataFrame
            stats: Summary stats dict (assets, liabilities, equity, leverage)
        """
        base_row = results[results["shock_bp"] == 0]
        base_eve = base_row["eve"].iloc[0] if not base_row.empty else 0
        worst = results.loc[results["change_$"].idxmin()]
        best = results.loc[results["change_$"].idxmax()]
        max_decline_pct = abs(results["change_%"].min())
        basel_threshold = 15.0

        if max_decline_pct > basel_threshold:
            compliance = "EXCEEDS Basel IRRBB outlier threshold (>15% EVE decline)"
        elif max_decline_pct > basel_threshold * 0.8:
            compliance = "APPROACHING Basel IRRBB threshold; enhanced monitoring recommended"
        else:
            compliance = "WITHIN Basel IRRBB limits; continue quarterly monitoring"

        prompt = f"""Write a concise IRRBB risk report in markdown for a bank risk manager.

Use only the facts below. Be specific with numbers. Include:
1. Executive summary (3-4 sentences)
2. Balance sheet risk drivers
3. Scenario sensitivity (cite worst/best cases)
4. Regulatory view vs the 15% Basel EVE outlier threshold
5. 3 prioritized actions

BALANCE SHEET
{bs.to_string(index=False)}

SUMMARY
- Total assets: ${stats.get('total_assets', 0):,.0f}
- Total liabilities: ${stats.get('total_liabilities', 0):,.0f}
- Equity: ${stats.get('equity', 0):,.0f}
- Leverage ratio: {stats.get('leverage_ratio', 0):.2f}x
- Weighted avg maturity: {stats.get('weighted_avg_maturity', 0):.2f} years

SENSITIVITY RESULTS
{results.to_string(index=False)}

KEY FIGURES
- Base EVE: ${base_eve:,.2f}
- Worst case: {worst['scenario']} → ${worst['change_$']:,.2f} ({worst['change_%']:+.2f}%)
- Best case: {best['scenario']} → ${best['change_$']:,.2f} ({best['change_%']:+.2f}%)
- Max EVE decline: {max_decline_pct:.2f}%
- Compliance snapshot: {compliance}
"""

        response = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a senior IRRBB analyst. Write clear, quantitative "
                        "markdown. Do not invent data that is not provided."
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
        return response.content
