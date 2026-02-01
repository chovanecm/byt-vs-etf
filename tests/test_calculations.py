import unittest
import sys
import os

# Add parent directory to sys.path to allow importing calculations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculations import calculate_metrics

class TestCalculations(unittest.TestCase):
    
    def test_basic_cashflow_no_mortgage(self):
        """Test cashflow with 100% down payment (no mortgage), no tax, no vacancy."""
        result = calculate_metrics(
            purchase_price=5_000_000,
            down_payment=5_000_000,
            one_off_costs=0,
            interest_rate=0,
            loan_term_years=30,
            monthly_rent=20_000,
            monthly_expenses=5_000,
            vacancy_months=0,
            tax_rate=0,
            appreciation_rate=0,
            rent_growth_rate=0,
            holding_period=1,
            etf_comparison=False,
            etf_return=0,
            initial_fx_rate=25,
            fx_appreciation=0
        )
        
        # Expected monthly CF for year 1:
        # (20000 * 12 - 5000 * 12) / 12 = 15000
        self.assertAlmostEqual(result["monthly_cashflow_y1"], 15_000)
        self.assertAlmostEqual(result["tax_paid_y1"], 0)

    def test_mortgage_calculation(self):
        """Test partial mortgage calculation logic."""
        # 5M price, 4M mortgage (20% down), 5% interest, 30 years
        # PMT should be roughly calculated by numpy_financial
        # But we just check the cashflow is reduced by mortgage payment
        
        result = calculate_metrics(
            purchase_price=5_000_000,
            down_payment=1_000_000,
            one_off_costs=0,
            interest_rate=5.0, # 5%
            loan_term_years=30,
            monthly_rent=20_000,
            monthly_expenses=0,
            vacancy_months=0,
            tax_rate=0,
            appreciation_rate=0,
            rent_growth_rate=0,
            holding_period=1,
            etf_comparison=False,
            etf_return=0,
            initial_fx_rate=25,
            fx_appreciation=0
        )
        
        # Mortgage Amount = 4M
        # Monthly Rate = 0.05 / 12 = 0.0041666...
        # Num payments = 360
        # PMT ~ 21,472.
        # Monthly CF = 20,000 - 21,472 = -1472
        
        self.assertLess(result["monthly_cashflow_y1"], 0)
        self.assertTrue(result["monthly_cashflow_y1"] > -2000) # Should be around -1500

    def test_tax_calculation(self):
        """Test income tax deduction."""
        # Rent 20k, Expenses 0, Mortgage 0.
        # Taxable income = 240k. Tax 15% = 36k/year = 3k/month.
        # Net CF = 17k/month.
        
        result = calculate_metrics(
            purchase_price=1_000_000,
            down_payment=1_000_000, # Full cash
            one_off_costs=0,
            interest_rate=0,
            loan_term_years=10,
            monthly_rent=20_000,
            monthly_expenses=0,
            vacancy_months=0,
            tax_rate=15,
            appreciation_rate=0,
            rent_growth_rate=0,
            holding_period=1,
            etf_comparison=False,
            etf_return=0,
            initial_fx_rate=25,
            fx_appreciation=0
        )
        
        self.assertAlmostEqual(result["monthly_cashflow_y1"], 17_000)
        # result["tax_paid_y1"] returns tax_y1 which is annual.
        # So 240k * 0.15 = 36k.
        self.assertAlmostEqual(result["tax_paid_y1"], 36_000)

    def test_etf_override(self):
        """Test ETF comparison logic returns values."""
        result = calculate_metrics(
            purchase_price=5_000_000,
            down_payment=1_000_000,
            one_off_costs=0,
            interest_rate=0,
            loan_term_years=30,
            monthly_rent=10_000,
            monthly_expenses=0,
            vacancy_months=0,
            tax_rate=0,
            appreciation_rate=0,
            rent_growth_rate=0,
            holding_period=10,
            etf_comparison=True, # ON
            etf_return=5.0,
            initial_fx_rate=25,
            fx_appreciation=0
        )
        
        self.assertIsNotNone(result["etf_irr"])
        # ETF IRR should be roughly 5% since appreciation is 5% and fx is stable.
        self.assertAlmostEqual(result["etf_irr"], 5.0, delta=0.5)

if __name__ == '__main__':
    unittest.main()
