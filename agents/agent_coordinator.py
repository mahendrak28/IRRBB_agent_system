"""
Multi-Agent Coordinator System - Fixed Version
Demonstrates agent orchestration, performance tracking, and evaluation
"""

import os
import time
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    print("⚠️  LangChain not fully configured, using fallback mode")
    LANGCHAIN_AVAILABLE = False

load_dotenv()

# Agent performance tracker
class AgentPerformanceTracker:
    """Track performance metrics for each agent"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_task(self, agent_name: str, task_id: str):
        """Start tracking a task"""
        if agent_name not in self.metrics:
            self.metrics[agent_name] = {
                'tasks': [],
                'total_time': 0,
                'total_tokens': 0,
                'total_cost': 0,
                'success_count': 0,
                'failure_count': 0
            }
        
        return {
            'agent_name': agent_name,
            'task_id': task_id,
            'start_time': time.time()
        }
    
    def end_task(self, tracking_info: Dict, success: bool, 
                  tokens_used: int = 0, response: Any = None):
        """End tracking and record metrics"""
        agent_name = tracking_info['agent_name']
        duration = time.time() - tracking_info['start_time']
        
        # Calculate cost (GPT-4o-mini pricing)
        cost = tokens_used * 0.00000015  # $0.15 per 1M tokens
        
        task_record = {
            'task_id': tracking_info['task_id'],
            'duration': duration,
            'tokens': tokens_used,
            'cost': cost,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        self.metrics[agent_name]['tasks'].append(task_record)
        self.metrics[agent_name]['total_time'] += duration
        self.metrics[agent_name]['total_tokens'] += tokens_used
        self.metrics[agent_name]['total_cost'] += cost
        
        if success:
            self.metrics[agent_name]['success_count'] += 1
        else:
            self.metrics[agent_name]['failure_count'] += 1
    
    def get_agent_performance(self, agent_name: str) -> Dict:
        """Get performance summary for an agent"""
        if agent_name not in self.metrics:
            return None
        
        metrics = self.metrics[agent_name]
        total_tasks = len(metrics['tasks'])
        
        if total_tasks == 0:
            return {'agent': agent_name, 'status': 'No tasks completed'}
        
        return {
            'agent': agent_name,
            'total_tasks': total_tasks,
            'success_rate': metrics['success_count'] / total_tasks * 100,
            'avg_response_time': metrics['total_time'] / total_tasks,
            'total_tokens': metrics['total_tokens'],
            'total_cost': metrics['total_cost'],
            'avg_cost_per_task': metrics['total_cost'] / total_tasks
        }
    
    def get_all_performance(self) -> Dict:
        """Get performance for all agents"""
        return {
            agent: self.get_agent_performance(agent)
            for agent in self.metrics.keys()
        }


# Specialized Agents
class ResearchAgent:
    """Fetches and processes market data"""
    
    def __init__(self, tracker: AgentPerformanceTracker):
        self.name = "ResearchAgent"
        self.tracker = tracker
        
        # Initialize LLM if available
        if LANGCHAIN_AVAILABLE:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                self.use_ai = True
            except Exception as e:
                print(f"⚠️  Could not initialize LLM: {e}")
                self.use_ai = False
        else:
            self.use_ai = False
    
    def fetch_market_context(self, base_rate: float) -> Dict:
        """Analyze market conditions"""
        task_id = f"research_{datetime.now().timestamp()}"
        tracking = self.tracker.start_task(self.name, task_id)
        
        try:
            if self.use_ai:
                # Use AI to analyze
                prompt = f"""Given a 10-year Treasury rate of {base_rate*100:.2f}%, provide a brief market assessment.
Respond with only 3 words describing market condition (e.g., "moderately volatile market")."""
                
                response = self.llm.invoke([HumanMessage(content=prompt)])
                condition = response.content.strip()
                tokens = len(prompt.split()) + len(response.content.split())
            else:
                # Use rule-based logic
                if base_rate > 0.05:
                    condition = "high rate environment"
                elif base_rate > 0.03:
                    condition = "moderate rate environment"
                else:
                    condition = "low rate environment"
                tokens = 10
            
            # Determine trend and outlook based on rate
            if base_rate > 0.045:
                trend = "rising"
                outlook = "hawkish"
            elif base_rate < 0.035:
                trend = "falling"
                outlook = "dovish"
            else:
                trend = "stable"
                outlook = "neutral"
            
            result = {
                "condition": condition,
                "trend": trend,
                "outlook": outlook
            }
            
            self.tracker.end_task(tracking, True, tokens, result)
            return result
            
        except Exception as e:
            print(f"   ⚠️  ResearchAgent error: {e}")
            self.tracker.end_task(tracking, False, 0)
            return {
                "condition": "unknown", 
                "trend": "unknown", 
                "outlook": "unknown"
            }


class AnalysisAgent:
    """Performs risk calculations and analysis"""
    
    def __init__(self, tracker: AgentPerformanceTracker):
        self.name = "AnalysisAgent"
        self.tracker = tracker
    
    def calculate_metrics(self, base_eve: float, shocked_eve: float, 
                         shock_bp: int) -> Dict:
        """Calculate risk metrics"""
        task_id = f"analysis_{datetime.now().timestamp()}"
        tracking = self.tracker.start_task(self.name, task_id)
        
        try:
            change = shocked_eve - base_eve
            change_pct = (change / abs(base_eve)) * 100 if base_eve != 0 else 0
            
            # Determine risk level
            if abs(change_pct) > 15:
                risk_level = "HIGH"
            elif abs(change_pct) > 10:
                risk_level = "ELEVATED"
            elif abs(change_pct) > 5:
                risk_level = "MODERATE"
            else:
                risk_level = "LOW"
            
            result = {
                'shock_scenario': f"{shock_bp:+d}bp",
                'eve_change_dollars': change,
                'eve_change_percent': change_pct,
                'risk_level': risk_level,
                'basel_compliant': abs(change_pct) < 15
            }
            
            # No LLM call, just math
            self.tracker.end_task(tracking, True, 5, result)
            return result
            
        except Exception as e:
            print(f"   ⚠️  AnalysisAgent error: {e}")
            self.tracker.end_task(tracking, False, 0)
            return {"error": str(e)}


class RecommendationAgent:
    """Generates actionable recommendations"""
    
    def __init__(self, tracker: AgentPerformanceTracker):
        self.name = "RecommendationAgent"
        self.tracker = tracker
        
        # Initialize LLM if available
        if LANGCHAIN_AVAILABLE:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.3,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                self.use_ai = True
            except Exception as e:
                print(f"⚠️  Could not initialize LLM: {e}")
                self.use_ai = False
        else:
            self.use_ai = False
    
    def generate_recommendation(self, analysis: Dict, market_context: Dict) -> Dict:
        """Generate actionable recommendations"""
        task_id = f"recommendation_{datetime.now().timestamp()}"
        tracking = self.tracker.start_task(self.name, task_id)
        
        try:
            risk_level = analysis.get('risk_level', 'UNKNOWN')
            eve_change = analysis.get('eve_change_percent', 0)
            
            if self.use_ai:
                # Use AI for recommendation
                prompt = f"""Risk Level: {risk_level}, EVE Change: {eve_change:.1f}%
Provide ONE specific action for risk management (max 12 words)."""
                
                response = self.llm.invoke([HumanMessage(content=prompt)])
                action = response.content.strip()
                tokens = len(prompt.split()) + len(response.content.split())
            else:
                # Rule-based recommendations
                if risk_level == "HIGH":
                    action = "Implement immediate hedging strategy with interest rate swaps"
                elif risk_level == "ELEVATED":
                    action = "Monitor closely and prepare contingent hedging plan"
                elif risk_level == "MODERATE":
                    action = "Review asset-liability mix and duration gap"
                else:
                    action = "Continue quarterly monitoring of interest rate exposure"
                tokens = 15
            
            priority = 'HIGH' if risk_level in ['HIGH', 'ELEVATED'] else 'MEDIUM'
            
            result = {
                'action': action,
                'priority': priority,
                'based_on': {
                    'risk_level': risk_level,
                    'eve_change': f"{eve_change:.2f}%"
                }
            }
            
            self.tracker.end_task(tracking, True, tokens, result)
            return result
            
        except Exception as e:
            print(f"   ⚠️  RecommendationAgent error: {e}")
            self.tracker.end_task(tracking, False, 0)
            return {
                "action": "Review risk exposure manually",
                "priority": "MEDIUM"
            }


class AgentCoordinator:
    """Orchestrates multi-agent workflow"""
    
    def __init__(self):
        print("🔧 Initializing Multi-Agent System...")
        self.tracker = AgentPerformanceTracker()
        
        try:
            self.research_agent = ResearchAgent(self.tracker)
            print("   ✓ Research Agent initialized")
        except Exception as e:
            print(f"   ⚠️  Research Agent failed: {e}")
            raise
        
        try:
            self.analysis_agent = AnalysisAgent(self.tracker)
            print("   ✓ Analysis Agent initialized")
        except Exception as e:
            print(f"   ⚠️  Analysis Agent failed: {e}")
            raise
        
        try:
            self.recommendation_agent = RecommendationAgent(self.tracker)
            print("   ✓ Recommendation Agent initialized")
        except Exception as e:
            print(f"   ⚠️  Recommendation Agent failed: {e}")
            raise
        
        print("✅ All agents ready!\n")
    
    def run_full_analysis(self, base_rate: float, base_eve: float, 
                         shocked_eve: float, shock_bp: int) -> Dict:
        """
        Coordinate all agents for complete analysis
        
        Returns:
            Complete analysis with performance metrics
        """
        print(f"\n🤖 Starting Multi-Agent Analysis...")
        print(f"Scenario: {shock_bp:+d}bp shock\n")
        
        # Step 1: Research Agent
        print("📊 Research Agent: Analyzing market conditions...")
        market_context = self.research_agent.fetch_market_context(base_rate)
        print(f"   ✓ Market: {market_context.get('condition', 'unknown')}")
        
        # Step 2: Analysis Agent
        print("🧮 Analysis Agent: Calculating risk metrics...")
        analysis = self.analysis_agent.calculate_metrics(base_eve, shocked_eve, shock_bp)
        print(f"   ✓ Risk Level: {analysis.get('risk_level', 'unknown')}")
        
        # Step 3: Recommendation Agent
        print("💡 Recommendation Agent: Generating recommendations...")
        recommendation = self.recommendation_agent.generate_recommendation(
            analysis, market_context
        )
        print(f"   ✓ Action: {recommendation.get('action', 'N/A')}")
        
        # Compile results
        result = {
            'timestamp': datetime.now().isoformat(),
            'inputs': {
                'base_rate': base_rate,
                'shock_bp': shock_bp
            },
            'market_context': market_context,
            'analysis': analysis,
            'recommendation': recommendation,
            'agent_performance': self.tracker.get_all_performance()
        }
        
        return result
    
    def get_performance_dashboard(self) -> Dict:
        """Get performance metrics for all agents"""
        return self.tracker.get_all_performance()


# Demo
if __name__ == "__main__":
    print("="*80)
    print("MULTI-AGENT COORDINATOR SYSTEM - FIXED VERSION")
    print("="*80)
    print()
    
    try:
        # Initialize coordinator
        coordinator = AgentCoordinator()
        
        # Example scenario
        result = coordinator.run_full_analysis(
            base_rate=0.0418,
            base_eve=120000,
            shocked_eve=113046,
            shock_bp=100
        )
        
        print("\n" + "="*80)
        print("📋 FINAL REPORT")
        print("="*80)
        print(f"\nMarket Assessment:")
        for key, value in result['market_context'].items():
            print(f"  {key}: {value}")
        
        print(f"\nRisk Analysis:")
        for key, value in result['analysis'].items():
            print(f"  {key}: {value}")
        
        print(f"\nRecommendation:")
        print(f"  Action: {result['recommendation']['action']}")
        print(f"  Priority: {result['recommendation']['priority']}")
        
        print("\n" + "="*80)
        print("⚡ AGENT PERFORMANCE METRICS")
        print("="*80)
        
        for agent, metrics in result['agent_performance'].items():
            if metrics and 'total_tasks' in metrics:
                print(f"\n{agent}:")
                print(f"  Tasks Completed: {metrics['total_tasks']}")
                print(f"  Success Rate: {metrics['success_rate']:.1f}%")
                print(f"  Avg Response Time: {metrics['avg_response_time']:.3f}s")
                print(f"  Total Tokens: {metrics['total_tokens']}")
                print(f"  Total Cost: ${metrics['total_cost']:.6f}")
                print(f"  Cost per Task: ${metrics['avg_cost_per_task']:.6f}")
        
        print("\n" + "="*80)
        print("✅ Multi-Agent Analysis Complete!")
        print("="*80)
        print("\n💡 This demonstrates:")
        print("   • Agent specialization (Research, Analysis, Recommendation)")
        print("   • Performance tracking (time, tokens, cost, success rate)")
        print("   • Production patterns (error handling, fallback logic)")
        print("   • Orchestration (coordinator manages workflow)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check OPENAI_API_KEY in .env file")
        print("2. Make sure virtual environment is activated")
        print("3. Run: pip install langchain-openai")
        import traceback
        traceback.print_exc()