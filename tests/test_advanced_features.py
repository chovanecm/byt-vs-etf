import unittest
import sys
import os
import pandas as pd

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import calculations

class TestAdvancedFeatures(unittest.TestCase):
    
    def test_capital_gains_tax_time_test(self):
        """
        Test that Capital Gains Tax is applied only when holding period < time test limit.
        """
        # Common params
        params = dict(
            purchase_price=5_000_000,
            down_payment=5_000_000, # All cash to simplify
            one_off_costs=0,
            interest_rate=0,
            loan_term_years=30,
            monthly_rent=0,
            monthly_expenses=0,
            vacancy_months=0,
            tax_rate=15.0,
            appreciation_rate=10.0, # High appreciation = High Profit
            rent_growth_rate=0,
            etf_comparison=False,
            etf_return=0,
            initial_fx_rate=25,
            fx_appreciation=0,
            sale_fee_percent=0
        )
        
        # Scenario 1: Hold 5 years (Fail test at 10y)
        res_fail = calculations.calculate_metrics(
            holding_period=5,
            time_test_vars={"enabled": True, "years": 10},
            **params
        )
        
        # Purchase: 5M. Value 5y @ 10%: 5 * 1.1^5 = ~8.05M
        # Profit ~ 3.05M. Tax 15% ~ 450k.
        self.assertGreater(res_fail['capital_gains_tax'], 0, "Should pay tax if hold < test limit")
        
        # Scenario 2: Hold 15 years (Pass test at 10y)
        res_pass = calculations.calculate_metrics(
            holding_period=15,
            time_test_vars={"enabled": True, "years": 10},
            **params
        )
        
        self.assertEqual(res_pass['capital_gains_tax'], 0, "Should NOT pay tax if hold > test limit")

    def test_projection_equity_growth(self):
        """
        Regression test for 'Hold Strategy' projection.
        Ensures Mortgage Balance decreases over time, increasing Equity.
        """
        start_val = 5_000_000
        start_mtg = 4_000_000
        
        df = calculations.project_future_wealth(
            start_property_value=start_val,
            start_mortgage_balance=start_mtg,
            net_liquidation_value=1_000_000, # Irrelevant for Hold
            monthly_payment=20_000, # Some payment
            mortgage_rate=3.0,
            appreciation_rate=0, # No price growth, just debt paydown
            etf_return_rate=0,
            projection_years=5
        )
        
        # Initial Equity approx 1M.
        # After 5 years, debt should decrease, so Equity should increase (even with 0% appreciation)
        final_equity = df['NW_Hold'].iloc[-1]
        
        # Calculate expected debt paydown roughly
        # 20k * 12 * 5 = 1.2M total payments. Interest is on 4M -> ~120k/year.
        # Principal paydown ~ 1.2M - 600k = 600k.
        # New Debt ~ 3.4M. Equity ~ 1.6M.
        
        self.assertGreater(final_equity, 1_000_000, "Equity should increase as debt is paid down")
        
        # Check linearity/monotonicity
        self.assertTrue(df['NW_Hold'].is_monotonic_increasing, "Equity must grow if price is stable and debt is paid")

    def test_refinance_arbitrage_logic(self):
        """
        Test 'calculate_decision_metrics_for_price' correctly identifies profitable arbitrage.
        Situation: Low mortgage rate (locked), High ETF return, High Market Rate (but still profitable spread?).
        Actually Arbitrage usually means: Borrow Cheap -> Invest High.
        Here we define arbitrage as: Refinance (Borrow NEW money) -> Invest.
        If New Rate (5%) < ETF Return (8%), it is profitable to Cash Out.
        """
        
        res = calculations.calculate_decision_metrics_for_price(
            property_value=10_000_000,
            mortgage_balance=0, # Fully paid off, taking new loan
            purchase_price=5_000_000,
            one_off_costs=0,
            sale_fee_percent=0,
            tax_rate=0,
            time_test_vars={},
            holding_years=10,
            target_ltv_ref=50, # Take 5M loan
            market_ref_rate=4.0, # Borrow at 4%
            interest_rate_current=0,
            etf_return_rate=8.0 # Invest at 8%
        )
        
        # Cash Out = 5M.
        # Cost of Debt = 5M * 4% = 200k.
        # Yield on ETF = 5M * 8% = 400k.
        # Arbitrage = +200k.
        
        self.assertEqual(res['Refinance_CashOut'], 5_000_000)
        self.assertAlmostEqual(res['Refinance_Arbitrage_CZK'], 200_000, delta=100)

if __name__ == '__main__':
    unittest.main()
