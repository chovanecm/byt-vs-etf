import numpy as np
import calculations

def run_monte_carlo(
    n_simulations,
    # Base params (same as calculate_metrics)
    purchase_price, down_payment, one_off_costs,
    interest_rate, loan_term_years,
    monthly_rent, monthly_expenses, vacancy_months, tax_rate,
    holding_period,
    initial_fx_rate, fx_appreciation,
    # Variable base params (Mean)
    appreciation_rate_mean, rent_growth_rate_mean,
    etf_comparison, etf_return_mean,
    # Volatility params (Std Dev)
    appreciation_rate_std, rent_growth_rate_std, etf_return_std,
    # Tax params
    time_test_enabled=True, time_test_years=10, sale_fee_percent=0.0
):
    results = []
    holding_years = int(holding_period)
    
    # Pre-generate random scenarios for performance
    # Shape: (n_simulations, holding_years)
    app_scenarios = np.random.normal(appreciation_rate_mean, appreciation_rate_std, size=(n_simulations, holding_years))
    rent_scenarios = np.random.normal(rent_growth_rate_mean, rent_growth_rate_std, size=(n_simulations, holding_years))
    
    etf_scenarios = None
    if etf_comparison:
        etf_scenarios = np.random.normal(etf_return_mean, etf_return_std, size=(n_simulations, holding_years))
    
    time_test_vars = {"enabled": time_test_enabled, "years": time_test_years}

    for i in range(n_simulations):
        # Extract specific scenario rates
        app_rates = app_scenarios[i]
        rent_rates = rent_scenarios[i]
        etf_rates = etf_scenarios[i] if etf_comparison else 0
        
        # Facade call back to main calculator
        res = calculations.calculate_metrics(
            purchase_price=purchase_price,
            down_payment=down_payment,
            one_off_costs=one_off_costs,
            interest_rate=interest_rate,
            loan_term_years=loan_term_years,
            monthly_rent=monthly_rent,
            monthly_expenses=monthly_expenses,
            vacancy_months=vacancy_months,
            tax_rate=tax_rate,
            appreciation_rate=app_rates,   # Passing array
            rent_growth_rate=rent_rates,   # Passing array
            holding_period=holding_period,
            etf_comparison=etf_comparison,
            etf_return=etf_rates,          # Passing array
            initial_fx_rate=initial_fx_rate,
            fx_appreciation=fx_appreciation,
            time_test_vars=time_test_vars,
            sale_fee_percent=sale_fee_percent
        )
        results.append(res)
        
    return results
