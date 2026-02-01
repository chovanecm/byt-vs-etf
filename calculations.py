import numpy_financial as npf
import numpy as np

def calculate_metrics(
    purchase_price, down_payment, one_off_costs,
    interest_rate, loan_term_years,
    monthly_rent, monthly_expenses, vacancy_months, tax_rate,
    appreciation_rate, rent_growth_rate, holding_period,
    etf_comparison, etf_return, initial_fx_rate, fx_appreciation,
    time_test_vars=None, sale_fee_percent=0.0
):
    if time_test_vars is None:
        time_test_vars = {"enabled": True, "years": 10}

    mortgage_amount = max(0, purchase_price - down_payment)
    
    # 1. Splátka hypotéky
    if mortgage_amount > 0:
        monthly_rate = (interest_rate / 100) / 12
        num_payments = loan_term_years * 12
        monthly_mortgage_payment = npf.pmt(monthly_rate, num_payments, -mortgage_amount)
    else:
        monthly_rate = 0
        monthly_mortgage_payment = 0
    
    # 2. Cashflow (Year 1 calculation for display)
    annual_gross_rent = monthly_rent * (12 - vacancy_months)
    annual_expenses_total = monthly_expenses * 12
    annual_mortgage_payment = monthly_mortgage_payment * 12
    
    # Odhad úroku 1. rok pro daňový štít (zjednodušeně z celé jistiny)
    interest_payment_y1 = mortgage_amount * (interest_rate / 100)
    tax_base_y1 = annual_gross_rent - annual_expenses_total - interest_payment_y1
    tax_y1 = max(0, tax_base_y1 * (tax_rate / 100))
    
    annual_cashflow_year1 = annual_gross_rent - annual_mortgage_payment - annual_expenses_total - tax_y1
    
    initial_investment = down_payment + one_off_costs
    
    # ETF Setup
    etf_balance_eur = 0
    etf_values_czk = []
    etf_cashflows_arr = []
    
    if etf_comparison:
        etf_balance_eur = initial_investment / initial_fx_rate
        etf_cashflows_arr = [-initial_investment]

    # Helper for handling variable rates (Monte Carlo support)
    def get_rate(rate_input, year_idx):
        if isinstance(rate_input, (list, np.ndarray)):
            # year_idx is 0-based index for the current year being calculated
            if year_idx < len(rate_input):
                 return rate_input[year_idx]
            return rate_input[-1] # Fallback
        return rate_input

    # 3. Projekce
    yearly_cashflows_arr = [-initial_investment]
    total_cf_sum = 0
    
    current_monthly_rent = monthly_rent
    current_monthly_expenses = monthly_expenses
    
    # Trackers
    current_mortgage_balance = mortgage_amount
    current_value = purchase_price

    # Lists
    property_values = []
    mortgage_balances = []
    
    for year in range(1, int(holding_period) + 1):
        year_idx = year - 1
        
        # a) Value Increase
        # Support variable appreciation rate
        rate_app = get_rate(appreciation_rate, year_idx)
        current_value *= (1 + rate_app / 100)
        property_values.append(current_value)
        
        # b) Inflation
        if year > 1:
            rate_rent = get_rate(rent_growth_rate, year_idx)
            current_monthly_rent *= (1 + rate_rent / 100)
            current_monthly_expenses *= (1 + rate_rent / 100)
        
        # c) Cashflow Components
        curr_annual_gross_rent = current_monthly_rent * (12 - vacancy_months)
        curr_annual_expenses = current_monthly_expenses * 12
        
        # Interest Calculation needed for Tax
        interest_paid_this_year = 0
        if current_mortgage_balance > 0:
             # Zjednodušený výpočet úroku z počátečního zůstatku roku
             interest_paid_this_year = current_mortgage_balance * (interest_rate / 100)
        
        # Tax Calculation
        # Základ daně = Příjem - Výdaje - Úroky (zjednodušeně, bez odpisů nemovitosti, což je konzervativní)
        taxable_income = curr_annual_gross_rent - curr_annual_expenses - interest_paid_this_year
        tax_paid = max(0, taxable_income * (tax_rate / 100))
        
        # Net Cashflow
        curr_annual_cf = curr_annual_gross_rent - annual_mortgage_payment - curr_annual_expenses - tax_paid
        
        yearly_cashflows_arr.append(curr_annual_cf)
        total_cf_sum += curr_annual_cf
        
        # d) Mortgage Balance Update
        if mortgage_amount > 0:
            period_months = year * 12
            if period_months >= num_payments:
                 rem_balance = 0
            else:
                 rem_balance = npf.fv(monthly_rate, period_months, monthly_mortgage_payment, -mortgage_amount)
            if rem_balance < 0: rem_balance = 0
            current_mortgage_balance = rem_balance # Update pro další rok úroků
        else:
            rem_balance = 0
            
        mortgage_balances.append(rem_balance)
        
        # ETF
        if etf_comparison:
            rate_etf = get_rate(etf_return, year_idx)
            etf_balance_eur *= (1 + rate_etf / 100)
            
            year_contribution_czk = 0
            if curr_annual_cf < 0:
                # Dotace do nemovitosti => stejná částka do ETF
                year_contribution_czk = abs(curr_annual_cf)
                current_fx_rate = initial_fx_rate * ((1 + fx_appreciation / 100) ** year)
                contribution_eur = year_contribution_czk / current_fx_rate
                etf_balance_eur += contribution_eur
            
            current_fx_rate_end = initial_fx_rate * ((1 + fx_appreciation / 100) ** year)
            etf_value_now_czk = etf_balance_eur * current_fx_rate_end
            etf_values_czk.append(etf_value_now_czk)
            etf_cashflows_arr.append(-year_contribution_czk)
    
    # Results
    sale_price = property_values[-1]
    final_mortgage_balance = mortgage_balances[-1]
    
    # 1. Sale Transaction Costs (e.g., Real Estate Agent fee)
    sale_costs = sale_price * (sale_fee_percent / 100.0)
    
    # 2. Capital Gains Tax (Časový test)
    capital_gains_tax = 0
    if time_test_vars and time_test_vars.get("enabled", True):
        if holding_period < time_test_vars.get("years", 10):
            # Only taxable if held less than limit
            total_acquisition_cost = purchase_price + one_off_costs
            # Profit for tax = Sale Price - Sale Costs - Acquisition
            profit_on_sale = sale_price - sale_costs - total_acquisition_cost
            if profit_on_sale > 0:
                capital_gains_tax = profit_on_sale * (tax_rate / 100)
    
    # 3. Net Sale Proceeds
    # Proceeds = Sale Price - Mortgage - Sale Costs - Tax
    sale_proceeds = sale_price - final_mortgage_balance - sale_costs - capital_gains_tax
    
    yearly_cashflows_arr[-1] += sale_proceeds
    
    # IRR calculation handling
    try:
        irr = npf.irr(yearly_cashflows_arr) * 100
        if np.isnan(irr): irr = 0
    except:
        irr = 0
        
    total_profit = total_cf_sum + sale_proceeds - initial_investment
    
    etf_irr = 0
    if etf_comparison:
        final_etf_value_czk = etf_values_czk[-1]
        etf_cashflows_arr[-1] += final_etf_value_czk
        try:
            etf_irr = npf.irr(etf_cashflows_arr) * 100
            if np.isnan(etf_irr): etf_irr = 0
        except:
            etf_irr = 0
    
    return {
        "irr": irr,
        "total_profit": total_profit,
        "etf_irr": etf_irr,
        "monthly_cashflow_y1": annual_cashflow_year1 / 12,
        "tax_paid_y1": tax_y1,
        "capital_gains_tax": capital_gains_tax,
        "initial_investment": initial_investment,
        "series": {
            "property_values": property_values,
            "mortgage_balances": mortgage_balances,
            "cashflows": yearly_cashflows_arr, 
            "etf_values": etf_values_czk,
            "etf_cashflows": etf_cashflows_arr
        }
    }

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
        
        res = calculate_metrics(
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
