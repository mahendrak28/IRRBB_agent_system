"""
Multi-Agent IRRBB Orchestration System
Simpler version using function calling (works with current LangChain)
"""

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.simple_eve_calculator import SimpleEVECalculator

load_dotenv()


class IRRBBTools:
    """Collection of tools for IRRBB analysis"""
    
    def __init__(self):
        self.calc = SimpleEVECalculator()
    
    def calculate_eve_scenario(self, rate_shock: float) -> str:
        """Calculate EVE for specific rate shock"""
        bs = self.calc.create_sample_balance_sheet()
        base_eve = self.calc.calculate_eve_base(bs)
        shocked_eve = self.calc.calculate_eve_shocked(bs, rate_shock)
        change = shocked_eve - base_eve
        change_pct = (change / abs(base_eve)) * 100 if base_eve != 0 else 0
        
        risk_level = 'HIGH' if abs(change_pct) > 15 else 'MODERATE' if abs(change_pct) > 5 else 'LOW'
        
        return f"""EVE Analysis for {rate_shock*10000:+.0f}bp shock:
- Base EVE: ${base_eve:,.2f}
- Shocked EVE: ${shocked_eve:,.2f}
- Change: ${change:,.2f} ({change_pct:+.2f}%)
- Risk Level: {risk_level}"""
    
    def get_balance_sheet_summary(self) -> str:
        """Get balance sheet summary"""
        bs = self.calc.create_sample_balance_sheet()
        stats = self.calc.get_summary_stats(bs)
        
        return f"""BALANCE SHEET SUMMARY:
Assets: ${stats['total_assets']:,.0f}
Liabilities: ${stats['total_liabilities']:,.0f}
Equity: ${stats['equity']:,.0f}
Leverage Ratio: {stats['leverage_ratio']:.2f}x
Weighted Avg Maturity: {stats['weighted_avg_maturity']:.2f} years

Asset Breakdown:
{bs[bs['balance'] > 0][['product', 'balance', 'maturity_years']].to_string(index=False)}

Liability Breakdown:
{bs[bs['balance'] < 0][['product', 'balance', 'maturity_years']].to_string(index=False)}"""
    
    def run_full_sensitivity_analysis(self) -> str:
        """Run complete sensitivity analysis"""
        results = self.calc.run_sensitivity_analysis()
        
        base_eve = results[results['shock_bp'] == 0]['eve'].iloc[0]
        worst = results.loc[results['change_$'].idxmin()]
        best = results.loc[results['change_$'].idxmax()]
        
        return f"""FULL SENSITIVITY ANALYSIS:

{results.to_string(index=False)}

KEY FINDINGS:
- Base EVE: ${base_eve:,.2f}
- Worst Case: {worst['scenario']} → ${worst['change_$']:,.2f} ({worst['change_%']:.2f}%)
- Best Case: {best['scenario']} → ${best['change_$']:,.2f} ({best['change_%']:.2f}%)
- Maximum Downside Risk: ${results['change_$'].min():,.2f}"""
    
    def assess_regulatory_compliance(self, eve_change_pct: float) -> str:
        """Assess regulatory compliance"""
        if abs(eve_change_pct) > 15:
            status = "⚠️  EXCEEDS THRESHOLD"
            action = "Immediate remediation required"
        elif abs(eve_change_pct) > 10:
            status = "⚡ APPROACHING THRESHOLD"
            action = "Develop hedging strategy"
        else:
            status = "✅ WITHIN LIMITS"
            action = "Continue quarterly monitoring"
        
        return f"""REGULATORY ASSESSMENT (Basel IRRBB):
EVE Change: {eve_change_pct:+.2f}%
Status: {status}
Action Required: {action}

Basel Guideline: EVE decline >15% of Tier 1 capital = Supervisory outlier"""


class IRRBBMultiAgentSystem:
    """Multi-agent orchestration using function calling"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.tools = IRRBBTools()
        
        # Define available functions
        self.functions = [
            {
                "name": "calculate_eve_scenario",
                "description": "Calculate Economic Value of Equity for a specific interest rate shock scenario",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rate_shock": {
                            "type": "number",
                            "description": "Interest rate shock in decimal, e.g., 0.02 for 200bp"
                        }
                    },
                    "required": ["rate_shock"]
                }
            },
            {
                "name": "get_balance_sheet_summary",
                "description": "Get current balance sheet composition and risk metrics",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "run_full_sensitivity_analysis",
                "description": "Run complete Basel-compliant IRRBB sensitivity analysis with all scenarios",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "assess_regulatory_compliance",
                "description": "Assess regulatory compliance based on EVE change percentage",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "eve_change_pct": {
                            "type": "number",
                            "description": "EVE change as percentage"
                        }
                    },
                    "required": ["eve_change_pct"]
                }
            }
        ]
    
    def execute_function(self, function_name: str, arguments: dict) -> str:
        """Execute a tool function"""
        if function_name == "calculate_eve_scenario":
            return self.tools.calculate_eve_scenario(arguments.get("rate_shock", 0))
        elif function_name == "get_balance_sheet_summary":
            return self.tools.get_balance_sheet_summary()
        elif function_name == "run_full_sensitivity_analysis":
            return self.tools.run_full_sensitivity_analysis()
        elif function_name == "assess_regulatory_compliance":
            return self.tools.assess_regulatory_compliance(arguments.get("eve_change_pct", 0))
        else:
            return f"Unknown function: {function_name}"
    
    def analyze(self, query: str) -> dict:
        """Run analysis with function calling"""
        
        messages = [
            SystemMessage(content="""You are an expert IRRBB risk analyst with access to analytical tools.

Use the available functions to:
1. Gather accurate data
2. Perform calculations
3. Assess regulatory compliance
4. Provide actionable recommendations

Always use specific numbers and cite Basel requirements when relevant."""),
            HumanMessage(content=query)
        ]
        
        print("\n🤖 Agent thinking...\n")
        
        # Allow up to 5 function calls
        for iteration in range(5):
            response = self.llm.bind(functions=self.functions).invoke(messages)
            
            # Check if agent wants to call a function
            if hasattr(response, 'additional_kwargs') and 'function_call' in response.additional_kwargs:
                function_call = response.additional_kwargs['function_call']
                function_name = function_call['name']
                arguments = json.loads(function_call['arguments'])
                
                print(f"🔧 Calling tool: {function_name}")
                print(f"   Arguments: {arguments}")
                
                # Execute the function
                result = self.execute_function(function_name, arguments)
                
                print(f"✓ Tool result received\n")
                
                # Add function result to messages
                messages.append(response)
                messages.append(HumanMessage(content=f"Function result: {result}"))
                
            else:
                # Agent has final answer
                return {
                    'output': response.content,
                    'iterations': iteration + 1
                }
        
        return {
            'output': response.content if hasattr(response, 'content') else "Max iterations reached",
            'iterations': 5
        }


def run_demo():
    """Demo of multi-agent system"""
    
    print("="*80)
    print("🤖 MULTI-AGENT IRRBB ORCHESTRATION SYSTEM")
    print("="*80)
    print("\n💡 This system uses AI agents with specialized tools to analyze interest")
    print("   rate risk and provide regulatory-compliant recommendations.\n")
    
    print("Initializing agents...")
    
    try:
        system = IRRBBMultiAgentSystem()
        print("✓ System ready!\n")
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure OPENAI_API_KEY is set in .env file")
        return
    
    # Example queries
    queries = [
        "What is our EVE sensitivity to a 200bp rate increase? Is this compliant with Basel standards?",
        
        "Analyze our balance sheet and tell me what our biggest interest rate risk is.",
        
        "Run a full sensitivity analysis and identify the worst case scenario. What should we do about it?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}/{len(queries)}")
        print('='*80)
        print(f"❓ {query}\n")
        print("-"*80)
        
        try:
            result = system.analyze(query)
            
            print(f"\n📊 FINAL ANSWER:")
            print("-"*80)
            print(result['output'])
            print("-"*80)
            print(f"\n✓ Completed in {result['iterations']} iteration(s)")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        if i < len(queries):
            input("\n⏸  Press Enter to continue to next query...")
    
    print("\n" + "="*80)
    print("✅ DEMO COMPLETE!")
    print("="*80)
    print("\n🎯 What you just built:")
    print("   ✓ Multi-agent AI system")
    print("   ✓ Function calling / tool use")
    print("   ✓ Autonomous reasoning")
    print("   ✓ Regulatory compliance checking")
    print("   ✓ Professional financial analysis")
    print("\n💰 This is $200k+ level AI engineering!")
    print("\n📈 API cost for this demo: ~$0.01")


if __name__ == "__main__":
    run_demo()