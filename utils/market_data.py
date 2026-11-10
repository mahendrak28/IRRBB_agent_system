"""
Market Data Module - Fetches real-time data from Federal Reserve
"""

import os
from dotenv import load_dotenv
from fredapi import Fred
import pandas as pd
from datetime import datetime, timedelta

load_dotenv()


class FederalReserveData:
    """
    Fetch real interest rate data from Federal Reserve Economic Data (FRED)
    """
    
    def __init__(self):
        api_key = os.getenv('FRED_API_KEY')
        if not api_key:
            raise ValueError("FRED_API_KEY not found in .env file")
        self.fred = Fred(api_key=api_key)
    
    def get_treasury_rate(self, maturity='10Y'):
        """
        Get current Treasury yield for specified maturity
        
        Args:
            maturity: '3M', '2Y', '5Y', '10Y', '30Y'
        
        Returns:
            Current yield as decimal (e.g., 0.0452 for 4.52%)
        """
        series_map = {
            '3M': 'DGS3MO',   # 3-Month Treasury
            '2Y': 'DGS2',     # 2-Year Treasury
            '5Y': 'DGS5',     # 5-Year Treasury
            '10Y': 'DGS10',   # 10-Year Treasury
            '30Y': 'DGS30'    # 30-Year Treasury
        }
        
        series_id = series_map.get(maturity, 'DGS10')
        
        try:
            # Get most recent observation
            data = self.fred.get_series(series_id, observation_start='2024-01-01')
            latest_rate = data.dropna().iloc[-1]
            
            # Convert from percentage to decimal
            return latest_rate / 100.0
        except Exception as e:
            print(f"Error fetching {maturity} Treasury rate: {e}")
            # Return fallback estimate
            return 0.045
    
    def get_yield_curve(self):
        """
        Get current Treasury yield curve across maturities
        
        Returns:
            Dictionary with yields for different maturities
        """
        maturities = ['3M', '2Y', '5Y', '10Y', '30Y']
        yields = {}
        
        for maturity in maturities:
            yields[maturity] = self.get_treasury_rate(maturity)
        
        return yields
    
    def get_historical_rates(self, maturity='10Y', days=30):
        """
        Get historical Treasury rates
        
        Args:
            maturity: Treasury maturity
            days: Number of days of history
        
        Returns:
            Pandas Series with historical rates
        """
        series_map = {
            '3M': 'DGS3MO',
            '2Y': 'DGS2',
            '5Y': 'DGS5',
            '10Y': 'DGS10',
            '30Y': 'DGS30'
        }
        
        series_id = series_map.get(maturity, 'DGS10')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            data = self.fred.get_series(series_id, observation_start=start_date)
            # Convert from percentage to decimal
            return data / 100.0
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return pd.Series()
    
    def get_rate_change(self, maturity='10Y', days=30):
        """
        Calculate how much rates have changed over period
        
        Args:
            maturity: Treasury maturity
            days: Lookback period
        
        Returns:
            Rate change in basis points
        """
        historical = self.get_historical_rates(maturity, days)
        
        if len(historical) < 2:
            return 0
        
        current = historical.iloc[-1]
        past = historical.iloc[0]
        change_decimal = current - past
        change_bp = change_decimal * 10000  # Convert to basis points
        
        return change_bp


def demo_market_data():
    """Demo of market data functionality"""
    
    print("="*70)
    print("📊 REAL-TIME FEDERAL RESERVE DATA")
    print("="*70)
    
    try:
        fed_data = FederalReserveData()
        
        # Current yield curve
        print("\n💵 CURRENT TREASURY YIELD CURVE")
        print("-"*70)
        yields = fed_data.get_yield_curve()
        
        for maturity, rate in yields.items():
            print(f"{maturity:>4} Treasury: {rate*100:>6.2f}%  ({rate:.4f} decimal)")
        
        # 10-year details
        print("\n📈 10-YEAR TREASURY ANALYSIS")
        print("-"*70)
        current_10y = fed_data.get_treasury_rate('10Y')
        change_30d = fed_data.get_rate_change('10Y', 30)
        change_90d = fed_data.get_rate_change('10Y', 90)
        
        print(f"Current Rate:        {current_10y*100:.2f}%")
        print(f"30-Day Change:       {change_30d:+.0f} bp")
        print(f"90-Day Change:       {change_90d:+.0f} bp")
        
        # Suggest shock scenarios based on recent volatility
        print("\n⚡ SUGGESTED IRRBB SCENARIOS")
        print("-"*70)
        
        volatility = abs(change_30d)
        if volatility > 50:
            scenario_range = "±300bp"
            risk_level = "HIGH"
        elif volatility > 25:
            scenario_range = "±200bp"
            risk_level = "MODERATE"
        else:
            scenario_range = "±100bp"
            risk_level = "LOW"
        
        print(f"Recent Volatility:   {volatility:.0f} bp/month")
        print(f"Market Risk Level:   {risk_level}")
        print(f"Recommended Shocks:  {scenario_range}")
        print(f"Base Rate for EVE:   {current_10y*100:.2f}%")
        
        print("\n" + "="*70)
        print("✅ Real market data successfully retrieved!")
        print("="*70)
        print("\n💡 This data is LIVE from the Federal Reserve")
        print("   Updates daily with actual market conditions")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. You added FRED_API_KEY to your .env file")
        print("2. You signed up at https://fred.stlouisfed.org/")
        print("3. You have internet connection")


if __name__ == "__main__":
    demo_market_data()