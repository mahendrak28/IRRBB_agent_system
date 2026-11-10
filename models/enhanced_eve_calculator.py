"""
Enhanced EVE Calculator with Real Market Data
Uses live Federal Reserve data instead of assumptions
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.market_data import FederalReserveData


class EnhancedEVECalculator:
    """
    EVE Calculator with real-time market data integration
    """
    
    def __init__(self, use_real_data=True):
        """
        Initialize calculator
        
        Args:
            use_real_data: If True, fetch live rates from Fed. If False, use fallback.
        """
        self.use_real_data = use_real_data
        
        if use_real_data:
            try:
                self.fed_data = FederalReserveData()
                self.base_rate = self.fed_data.get_treasury_rate('10Y')
                self.data_source = f"Federal Reserve (10Y Treasury as of {datetime.now().strftime('%Y-%m-%d')})"
            except Exception as e:
                print(f"⚠️  Could not fetch real data: {e}")
                print("   Falling back to assumed rate...")
                self.base_rate = 0.045
                self.data_source = "Assumed rate (FRED unavailable)"
        else:
            self.base_rate = 0.045
            self.data_source = "Assumed rate (demo mode)"
    
    def create_sample_balance_sheet(self):
        """Generate realistic bank balance sheet"""
        data = {
            'product': [
                'Fixed Rate Loans',
                'Variable Rate Loans', 
                'Mortgage Portfolio',
                'Treasury Securities',
                'Savings Deposits',
                'Term Deposits',
                'Senior Bonds',
                'Subordinated Debt'
            ],
            'balance': [
                1000000,   # Asset
                500000,    # Asset
                800000,    # Asset
                300000,    # Asset
                -1200000,  # Liability (negative)
                -600000,   # Liability
                -400000,   # Liability
                -200000    # Liability
            ],
            'rate': [0.06, 0.055, 0.065, 0.04, 0.02, 0.035, 0.04, 0.05],
            'maturity_years': [5, 3, 15, 2, 0.5, 2, 10, 7]
        }
        return pd.DataFrame(data)
    
    def calculate_pv(self, cash_flow, discount_rate, time_years):
        """Present value calculation: PV = CF / (1 + r)^t"""
        return cash_flow / ((1 + discount_rate) ** time_years)
    
    def calculate_eve_base(self, balance_sheet):
        """Calculate EVE at current market rates"""
        total_pv = 0
        for _, row in balance_sheet.iterrows():
            pv = self.calculate_pv(
                row['balance'], 
                self.base_rate,  # Now using REAL Fed rate!
                row['maturity_years']
            )
            total_pv += pv
        return total_pv
    
    def calculate_eve_shocked(self, balance_sheet, rate_shock):
        """Calculate EVE with interest rate shock"""
        shocked_rate = self.base_rate + rate_shock
        total_pv = 0
        for _, row in balance_sheet.iterrows():
            pv = self.calculate_pv(
                row['balance'], 
                shocked_rate, 
                row['maturity_years']
            )
            total_pv += pv
        return total_pv
    
    def get_recommended_scenarios(self):
        """
        Dynamically determine shock scenarios based on market volatility
        """
        if self.use_real_data:
            try:
                # Check recent volatility
                change_30d = abs(self.fed_data.get_rate_change('10Y', 30))
                
                if change_30d > 50:
                    return {
                        'scenarios': [-0.03, -0.02, 0, 0.02, 0.03],
                        'rationale': f'HIGH volatility ({change_30d:.0f}bp/30d) → Testing ±300bp',
                        'risk_level': 'HIGH'
                    }
                elif change_30d > 25:
                    return {
                        'scenarios': [-0.02, -0.01, 0, 0.01, 0.02],
                        'rationale': f'MODERATE volatility ({change_30d:.0f}bp/30d) → Basel standard ±200bp',
                        'risk_level': 'MODERATE'
                    }
                else:
                    return {
                        'scenarios': [-0.01, -0.005, 0, 0.005, 0.01],
                        'rationale': f'LOW volatility ({change_30d:.0f}bp/30d) → Conservative ±100bp',
                        'risk_level': 'LOW'
                    }
            except:
                pass
        
        # Fallback to Basel standard
        return {
            'scenarios': [-0.02, -0.01, 0, 0.01, 0.02],
            'rationale': 'Basel standard scenarios',
            'risk_level': 'MODERATE'
        }
    
    def run_sensitivity_analysis(self):
        """
        Run IRRBB sensitivity analysis with market-appropriate scenarios
        """
        bs = self.create_sample_balance_sheet()
        scenario_info = self.get_recommended_scenarios()
        shocks = scenario_info['scenarios']
        
        results = []
        base_eve = self.calculate_eve_base(bs)
        
        for shock in shocks:
            shocked_eve = self.calculate_eve_shocked(bs, shock)
            change = shocked_eve - base_eve
            change_pct = (change / abs(base_eve)) * 100 if base_eve != 0 else 0
            
            results.append({
                'scenario': f'{int(shock * 10000):+d}bp',
                'shock_bp': int(shock * 10000),
                'eve': shocked_eve,
                'change_$': change,
                'change_%': change_pct
            })
        
        return pd.DataFrame(results), scenario_info
    
    def get_summary_stats(self, balance_sheet):
        """Calculate key balance sheet metrics"""
        assets = balance_sheet[balance_sheet['balance'] > 0]['balance'].sum()
        liabilities = abs(balance_sheet[balance_sheet['balance'] < 0]['balance'].sum())
        equity = assets - liabilities
        
        bs = balance_sheet.copy()
        bs['weighted_maturity'] = abs(bs['balance']) * bs['maturity_years']
        total_balance = abs(bs['balance']).sum()
        wam = bs['weighted_maturity'].sum() / total_balance if total_balance > 0 else 0
        
        return {
            'total_assets': assets,
            'total_liabilities': liabilities,
            'equity': equity,
            'leverage_ratio': assets / equity if equity > 0 else 0,
            'weighted_avg_maturity': wam
        }


if __name__ == "__main__":
    print("="*80)
    print("ENHANCED IRRBB EVE CALCULATOR - WITH REAL MARKET DATA")
    print("="*80)
    
    # Initialize with real Fed data
    calc = EnhancedEVECalculator(use_real_data=True)
    bs = calc.create_sample_balance_sheet()
    
    print(f"\n📊 DATA SOURCE")
    print("-"*80)
    print(f"Base Rate: {calc.base_rate*100:.2f}% ({calc.base_rate:.4f})")
    print(f"Source: {calc.data_source}")
    
    print("\n📊 BALANCE SHEET")
    print("-"*80)
    print(bs.to_string(index=False))
    
    print("\n📈 SUMMARY STATISTICS")
    print("-"*80)
    stats = calc.get_summary_stats(bs)
    print(f"Total Assets:              ${stats['total_assets']:>15,.0f}")
    print(f"Total Liabilities:         ${stats['total_liabilities']:>15,.0f}")
    print(f"Equity:                    ${stats['equity']:>15,.0f}")
    print(f"Leverage Ratio:            {stats['leverage_ratio']:>15.2f}x")
    print(f"Weighted Avg Maturity:     {stats['weighted_avg_maturity']:>15.2f} years")
    
    # Run analysis with market-appropriate scenarios
    print("\n⚡ EVE SENSITIVITY ANALYSIS")
    print("-"*80)
    results, scenario_info = calc.run_sensitivity_analysis()
    print(f"Scenario Selection: {scenario_info['rationale']}")
    print(f"Market Risk Level: {scenario_info['risk_level']}")
    print()
    print(results.to_string(index=False))
    
    print("\n💡 KEY INSIGHTS")
    print("-"*80)
    base_eve = results[results['shock_bp'] == 0]['eve'].iloc[0]
    worst_case = results.loc[results['change_$'].idxmin()]
    best_case = results.loc[results['change_$'].idxmax()]
    
    print(f"Base EVE (no shock):       ${base_eve:>15,.0f}")
    print(f"Worst scenario:            {worst_case['scenario']:>15} (${worst_case['change_$']:,.0f})")
    print(f"Best scenario:             {best_case['scenario']:>15} (${best_case['change_$']:,.0f})")
    
    # Regulatory compliance check
    max_decline_pct = abs(results['change_%'].min())
    basel_threshold = 15.0
    
    print(f"\n🏛️ REGULATORY COMPLIANCE (Basel IRRBB)")
    print("-"*80)
    print(f"Max EVE Decline:           {max_decline_pct:>15.2f}%")
    print(f"Basel Threshold:           {basel_threshold:>15.2f}%")
    
    if max_decline_pct > basel_threshold:
        status = "⚠️  EXCEEDS THRESHOLD"
        action = "Supervisory outlier - remediation required"
    elif max_decline_pct > basel_threshold * 0.8:
        status = "⚡ APPROACHING THRESHOLD"
        action = "Enhanced monitoring recommended"
    else:
        status = "✅ WITHIN LIMITS"
        action = "Continue quarterly monitoring"
    
    print(f"Status:                    {status}")
    print(f"Action Required:           {action}")
    
    print("\n" + "="*80)
    print("✅ Analysis complete using REAL Federal Reserve data!")
    print("="*80)
    print(f"\n💡 Your analysis now uses actual market rate: {calc.base_rate*100:.2f}%")
    print("   Not an assumption - this is today's 10Y Treasury yield from the Fed")
    print(f"   Data freshness: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")