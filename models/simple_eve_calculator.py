"""
Economic Value of Equity (EVE) Calculator for IRRBB
Foundation for Interest Rate Risk in the Banking Book modeling
"""

import pandas as pd
import numpy as np
from datetime import datetime

class SimpleEVECalculator:
    """
    EVE Calculator - measures bank's sensitivity to interest rate changes
    This is what regulators require under Basel IRRBB guidelines
    """
    
    def __init__(self, base_rate=0.05):
        self.base_rate = base_rate
        
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
        """Calculate EVE at current rates (no shock)"""
        total_pv = 0
        for _, row in balance_sheet.iterrows():
            pv = self.calculate_pv(
                row['balance'], 
                self.base_rate, 
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
    
    def run_sensitivity_analysis(self):
        """
        Run Basel-compliant rate shock scenarios
        Tests: -200bp, -100bp, Base, +100bp, +200bp
        """
        bs = self.create_sample_balance_sheet()
        shocks = [-0.02, -0.01, 0, 0.01, 0.02]
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
        
        return pd.DataFrame(results)
    
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
    print("="*70)
    print("IRRBB EVE CALCULATOR - BASELINE MODEL")
    print("="*70)
    
    calc = SimpleEVECalculator()
    bs = calc.create_sample_balance_sheet()
    
    print("\n📊 BALANCE SHEET")
    print("-"*70)
    print(bs.to_string(index=False))
    
    print("\n📈 SUMMARY STATISTICS")
    print("-"*70)
    stats = calc.get_summary_stats(bs)
    print(f"Total Assets:              ${stats['total_assets']:>15,.0f}")
    print(f"Total Liabilities:         ${stats['total_liabilities']:>15,.0f}")
    print(f"Equity:                    ${stats['equity']:>15,.0f}")
    print(f"Leverage Ratio:            {stats['leverage_ratio']:>15.2f}x")
    print(f"Weighted Avg Maturity:     {stats['weighted_avg_maturity']:>15.2f} years")
    
    print("\n⚡ EVE SENSITIVITY ANALYSIS (Basel Scenarios)")
    print("-"*70)
    results = calc.run_sensitivity_analysis()
    print(results.to_string(index=False))
    
    print("\n💡 KEY INSIGHTS")
    print("-"*70)
    base_eve = results[results['shock_bp'] == 0]['eve'].iloc[0]
    worst_case = results.loc[results['change_$'].idxmin()]
    best_case = results.loc[results['change_$'].idxmax()]
    
    print(f"Base EVE (no shock):       ${base_eve:>15,.0f}")
    print(f"Worst scenario:            {worst_case['scenario']:>15} (${worst_case['change_$']:,.0f})")
    print(f"Best scenario:             {best_case['scenario']:>15} (${best_case['change_$']:,.0f})")
    print(f"EVE at Risk (200bp up):    ${results[results['shock_bp']==200]['change_$'].iloc[0]:>15,.0f}")
    
    print("\n" + "="*70)
    print("✅ Model complete! Ready for AI agent analysis...")
    print("="*70)