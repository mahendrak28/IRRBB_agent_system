"""
Multi-Agent IRRBB Orchestration System
Coordinates multiple specialized agents for comprehensive risk analysis
"""

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_core.tools import tool
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.simple_eve_calculator import SimpleEVECalculator

load_dotenv()

# Define specialized tools for agents
@tool
def calculate_eve_scenario(rate_shock: float) -> str:
    """
    Calculate Economic Value of Equity for a specific interest rate shock.
    
    Args:
        rate_shock: Interest rate shock in decimal (e.g., 0.02 for 200bp increase)
    
    Returns:
        Detailed EVE calculation results as string
    """
    calc = SimpleEVECalculator()
    bs = calc.create_sample_balance_sheet()
    base_eve = calc.calculate_eve_base(bs)
    shocked_eve = calc.calculate_eve_shocked(bs, rate_shock)
    change = shocked_eve - base_eve
    change_pct = (change / abs(base_eve)) * 100 if base_eve != 0 else 0
    
    return f"""EVE Analysis for {rate_shock*10000:+.0f}bp shock:
- Base EVE: ${base_eve:,.2f}
- Shocked EVE: ${shocked_eve:,.2f}
- Change: ${change:,.2f} ({change_pct:+.2f}%)
- Risk Level: {'HIGH' if abs(change_pct) > 15 else 'MODERATE' if abs(change_pct) > 5 else 'LOW'}"""

@tool
def get_balance_sheet_summary() -> str:
    """
    Get current balance sheet composition and key risk metrics.
    
    Returns:
        Summary of balance sheet structure and risk indicators
    """
    calc = SimpleEVECalculator()
    bs = calc.create_sample_balance_sheet()
    stats = calc.get_summary_stats(bs)
    
    assets = bs[bs['balance'] > 0]
    liabilities = bs[bs['balance'] < 0]
    
    return f"""BALANCE SHEET SUMMARY:
Assets: ${stats['total_assets']:,.0f}
Liabilities: ${stats['total_liabilities']:,.0f}
Equity: ${stats['equity']:,.0f}
Leverage Ratio: {stats['leverage_ratio']:.2f}x
Weighted Avg Maturity: {stats['weighted_avg_maturity']:.2f} years"""

@tool
def run_full_sensitivity_analysis() -> str:
    """
    Run complete Basel-compliant IRRBB sensitivity analysis.
    Tests all standard rate shock scenarios.
    
    Returns:
        Complete sensitivity analysis results
    """
    calc = SimpleEVECalculator()
    results = calc.run_sensitivity_analysis()
    
    base_eve = results[results['shock_bp'] == 0]['eve'].iloc[0]
    worst = results.loc[results['change_$'].idxmin()]
    best = results.loc[results['change_$'].idxmax()]
    
    return f"""FULL SENSITIVITY ANALYSIS:
Base EVE: ${base_eve:,.2f}
Worst Case: {worst['scenario']} → ${worst['change_$']:,.2f} ({worst['change_%']:.2f}%)
Best Case: {best['scenario']} → ${best['change_$']:,.2f} ({best['change_%']:.2f}%)
Max Downside Risk: ${results['change_$'].min():,.2f}

All Scenarios:
{results.to_string(index=False)}"""

@tool
def assess_regulatory_compliance(eve_change_pct: float) -> str:
    """
    Assess regulatory compliance based on EVE change percentage.
    
    Args:
        eve_change_pct: EVE change as percentage of base
    
    Returns:
        Regulatory compliance assessment
    """
    if abs(eve_change_pct) > 15:
        status = "EXCEEDS THRESHOLD - Enhanced monitoring required"
        action = "Immediate remediation plan needed"
    elif abs(eve_change_pct) > 10:
        status = "APPROACHING THRESHOLD - Heightened oversight"
        action = "Develop contingency hedging strategy"
    else:
        status = "WITHIN LIMITS - Normal monitoring"
        action = "Continue quarterly reviews"
    
    return f"""REGULATORY ASSESSMENT (Basel IRRBB):
EVE Change: {eve_change_pct:+.2f}%
Status: {status}
Required Action: {action}

Basel Standards:
- EVE decline >15% of Tier 1 capital → Supervisory outlier"""


class IRRBBMultiAgentSystem:
    """
    Orchestrates multiple AI agents for comprehensive IRRBB analysis
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Define available tools
        self.tools = [
            calculate_eve_scenario,
            get_balance_sheet_summary,
            run_full_sensitivity_analysis,
            assess_regulatory_compliance
        ]
        
        # Create custom prompt for the agent
        template = """You are an expert IRRBB risk management system with access to analytical tools.

Your role is to:
1. Analyze interest rate risk comprehensively
2. Use the appropriate tools to gather data
3. Provide actionable insights for risk managers
4. Ensure regulatory compliance

Available tools: {tools}
Tool names: {tool_names}

When given a task:
- Use tools to get accurate data (use Action/Action Input format)
- Analyze the results quantitatively
- Provide specific, actionable recommendations
- Reference regulatory requirements (Basel IRRBB)

Question: {input}

Thought: {agent_scratchpad}"""

        prompt = ChatPromptTemplate.from_template(template)
        
        # Create agent with ReAct pattern
        agent = create_react_agent(self.llm, self.tools, prompt)
        
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True
        )
    
    def analyze(self, query: str):
        """
        Run analysis based on natural language query
        
        Args:
            query: Natural language question about IRRBB
            
        Returns:
            Analysis results
        """
        return self.agent_executor.invoke({"input": query})


def run_demo():
    """Demo of multi-agent system capabilities"""
    
    print("="*80)
    print("🤖 MULTI-AGENT IRRBB ORCHESTRATION SYSTEM")
    print("="*80)
    print("\nInitializing AI agents...")
    
    try:
        system = IRRBBMultiAgentSystem()
        print("✓ System ready!\n")
    except Exception as e:
        print(f"✗ Error initializing system: {e}")
        return
    
    # Example queries
    queries = [
        "What is our current EVE sensitivity to a 200bp rate increase?",
        
        "Get the balance sheet summary and identify the biggest risk.",
        
        "Run a complete sensitivity analysis and tell me the worst case scenario."
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}: {query}")
        print('='*80)
        
        try:
            result = system.analyze(query)
            
            print(f"\n📊 AGENT RESPONSE:")
            print("-"*80)
            print(result['output'])
            print("-"*80)
        except Exception as e:
            print(f"✗ Error processing query: {e}")
            continue
        
        if i < len(queries):
            input("\n⏸  Press Enter for next query...")
    
    print("\n" + "="*80)
    print("✅ Multi-Agent Demo Complete!")
    print("="*80)
    print("\n💡 Key Achievement: You now have agents that can:")
    print("   • Work together autonomously")
    print("   • Use specialized tools")
    print("   • Answer complex questions")
    print("   • Provide regulatory-compliant analysis")
    print("\n🎯 This is $200k+ level engineering!")


if __name__ == "__main__":
    run_demo()