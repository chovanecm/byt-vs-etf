import numpy_financial as npf
import numpy as np

def calculate_metrics(
    purchase_price, down_payment, one_off_costs,
    interest_rate, loan_term_years,
    monthly_rent, monthly_expenses, vacancy_months, tax_rate,
    appreciation_rate, rent_growth_rate, holding_period,
    etf_comparison, etf_return, initial_fx_rate, fx_appreciation
):
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

    # 3. Projekce
    yearly_cashflows_arr = [-initial_investment]
    total_cf_sum = 0
    
    current_monthly_rent = monthly_rent
    current_monthly_expenses = monthly_expenses
    
    # Trackers
    current_mortgage_balance = mortgage_amount

    # Lists
    property_values = []
    mortgage_balances = []
    
    for year in range(1, int(holding_period) + 1):
        # a) Value Increase
        current_value = purchase_price * ((1 + appreciation_rate / 100) ** year)
        property_values.append(current_value)
        
        # b) Inflation
        if year > 1:
            current_monthly_rent *= (1 + rent_growth_rate / 100)
            current_monthly_expenses *= (1 + rent_growth_rate / 100)
        
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
            etf_balance_eur *= (1 + etf_return / 100)
            
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
    sale_proceeds = sale_price - final_mortgage_balance
    
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
        "tax_paid_y1": tax_y1
    }
