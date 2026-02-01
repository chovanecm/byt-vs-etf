import unittest
import numpy_financial as npf
import sys
import os

# Add parent directory to path to import calculations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import calculations

class TestStrategyDiscrepancy(unittest.TestCase):
    def test_user_scenario_year_5(self):
        # --- 1. Establish Baseline (Model) to get Mortgage Balance at Year 5 ---
        purchase_price = 5_450_000
        interest_rate = 2.59
        loan_term_years = 30
        target_ltv_input = 90
        
        # Calculate Mortgage Amount
        mortgage_amount = purchase_price * (target_ltv_input / 100.0)
        down_payment = purchase_price - mortgage_amount
        
        # Other inputs
        one_off_costs = 350_000
        monthly_rent = 18000
        monthly_expenses = 3500
        vacancy_months = 0 # simplifying
        appreciation_rate = 5.0 # simplifying, mainly for model history
        rent_growth_rate = 2.0
        tax_rate = 15.0
        sale_fee_percent = 3.0
        
        # Run full metrics to get the state at Year 5
        metrics = calculations.calculate_metrics(
            purchase_price=purchase_price,
            down_payment=down_payment,
            one_off_costs=one_off_costs,
            interest_rate=interest_rate,
            loan_term_years=loan_term_years,
            monthly_rent=monthly_rent,
            monthly_expenses=monthly_expenses,
            vacancy_months=vacancy_months,
            tax_rate=tax_rate,
            appreciation_rate=appreciation_rate,
            rent_growth_rate=rent_growth_rate,
            holding_period=30, # generate long enough series
            etf_comparison=False,
            etf_return=0,
            initial_fx_rate=25,
            fx_appreciation=0,
            time_test_vars={"enabled": True, "years": 10},
            sale_fee_percent=sale_fee_percent
        )
        
        # Get Mortgage Balance at end of Year 5 (index 4)
        selected_year = 5
        mortgage_balance_y5 = metrics['series']['mortgage_balances'][selected_year-1]
        
        print(f"\n--- Model State at Year {selected_year} ---")
        print(f"Purchase Price: {purchase_price:,.0f}")
        print(f"Initial Mortgage: {mortgage_amount:,.0f}")
        print(f"Mortgage Balance Year {selected_year}: {mortgage_balance_y5:,.0f}")
        
        # --- 2. Apply User Override ---
        override_price = 7_000_000
        
        print(f"\n--- User Override ---")
        print(f"Override Price: {override_price:,.0f}")
        
        # --- 3. Calculate Decision Metrics ---
        decision = calculations.calculate_decision_metrics_for_price(
            property_value=override_price,
            mortgage_balance=mortgage_balance_y5,
            purchase_price=purchase_price,
            one_off_costs=one_off_costs,
            sale_fee_percent=sale_fee_percent,
            tax_rate=tax_rate,
            time_test_vars={"enabled": True, "years": 10},
            holding_years=selected_year,
            target_ltv_ref=80, # not critical for Net Liquidation
            market_ref_rate=4.5,
            interest_rate_current=interest_rate,
            etf_return_rate=8.0 # dummy
        )
        
        net_liquidation_value = decision['Net_Liquidation_Value']
        
        # --- 4. Manual Breakdown Calculation for Verification ---
        # Equity (Hold Strategy)
        equity_hold = override_price - mortgage_balance_y5
        
        # Sale Costs
        sale_fee = override_price * (sale_fee_percent / 100.0)
        
        # Tax Calculation
        total_acquisition_cost = purchase_price + one_off_costs
        gross_profit = override_price - sale_fee - total_acquisition_cost
        tax = 0
        if selected_year < 10: # Time test failed
             if gross_profit > 0:
                 tax = gross_profit * (tax_rate / 100.0)
        
        calculated_net_cash = override_price - mortgage_balance_y5 - sale_fee - tax
        
        print(f"\n--- Breakdown ---")
        print(f"1. STRATEGY HOLD (Net Equity): {equity_hold:,.0f} CZK")
        print(f"   (Price {override_price:,.0f} - Debt {mortgage_balance_y5:,.0f})")
        print(f"2. STRATEGY SELL (Net Cash):   {net_liquidation_value:,.0f} CZK")
        print(f"   Difference:                 {equity_hold - net_liquidation_value:,.0f} CZK")
        print(f"   composed of:")
        print(f"     - Sale Fee (3%):          {sale_fee:,.0f} CZK")
        print(f"     - Capital Gains Tax:      {tax:,.0f} CZK")
        print(f"     - Mortgage Payoff:        (included in both)")
        
        print(f"   Tax Base Calculation:")
        print(f"     Sale Price:               {override_price:,.0f}")
        print(f"     - Sale Fee:              -{sale_fee:,.0f}")
        print(f"     - Purchase Price:        -{purchase_price:,.0f}")
        print(f"     - Acquisition Costs:     -{one_off_costs:,.0f}")
        print(f"     = Gross Profit:           {gross_profit:,.0f}")
        
        # Assertions
        self.assertAlmostEqual(net_liquidation_value, calculated_net_cash, delta=1.0)
        
        # Check Refinance Cashout Check
        # Max Loan = 7,000,000 * 0.8 = 5,600,000
        # Current Debt = ~4,327,580
        # Cashout = 5.6M - 4.327M = 1,272,420
        max_loan = override_price * (80 / 100.0)
        expected_cashout = max(0, max_loan - mortgage_balance_y5)
        self.assertAlmostEqual(decision['Refinance_CashOut'], expected_cashout, delta=1.0)
        
        print(f"\nRefinance Cashout potential: {decision['Refinance_CashOut']:,.0f} CZK")

if __name__ == '__main__':
    unittest.main()
