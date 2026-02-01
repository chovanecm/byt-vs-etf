import numpy_financial as npf
import numpy as np
import pandas as pd
from logic.finance import calculate_mortgage_payment, update_remaining_balance
from logic import strategy
from logic import monte_carlo

# --- FACADE PATTERN ---
# This file now acts as an entry point (Facade) for backward compatibility
# and orchestration of logic modules.

def calculate_metrics(
    purchase_price, down_payment, one_off_costs,
    interest_rate, loan_term_years,
    monthly_rent, monthly_expenses, vacancy_months, tax_rate,
    appreciation_rate, rent_growth_rate, holding_period,
    etf_comparison, etf_return, initial_fx_rate, fx_appreciation,
    time_test_vars=None, sale_fee_percent=0.0, general_inflation_rate=None
):
    if time_test_vars is None:
        time_test_vars = {"enabled": True, "years": 10}
        
    # Default inflation if None (backward compatibility)
    if general_inflation_rate is None:
        # Use rent_growth_rate as proxy if not provided, or safe default 2.0
        # If rent_growth_rate is array (Monte Carlo), take mean or just 2.0
        if isinstance(rent_growth_rate, (list, np.ndarray)):
            general_inflation_rate = 2.0
        else:
            general_inflation_rate = rent_growth_rate

    mortgage_amount = max(0, purchase_price - down_payment)
    
    # 1. Splátka hypotéky - Delegated to logic/finance
    monthly_mortgage_payment, monthly_rate = calculate_mortgage_payment(
        mortgage_amount, interest_rate, loan_term_years
    )
    
    # 2. Cashflow (Year 1 calculation for display)
    annual_gross_rent = monthly_rent * (12 - vacancy_months)
    annual_expenses_total = monthly_expenses * 12
    annual_mortgage_payment = monthly_mortgage_payment * 12
    annual_cashflow_year1 = annual_gross_rent - annual_mortgage_payment - annual_expenses_total
    
    # Initial Investment
    initial_investment = down_payment + one_off_costs
    
    # --- TIME SERIES SIMULATION ---
    # Variables for loop
    current_property_value = purchase_price
    current_mortgage_balance = mortgage_amount
    
    curr_annual_gross_rent = annual_gross_rent
    curr_annual_expenses = annual_expenses_total
    
    yearly_cashflows_arr = [-initial_investment] # CF Year 0
    operating_cashflows = []
    
    property_values = []
    mortgage_balances = []
    
    # ETF Simulation Init
    etf_balance_eur = 0
    if etf_comparison:
        # Opportunity cost: Instead of buying flat, invest initial capital
        # Initial Capital in EUR
        etf_balance_eur = initial_investment / initial_fx_rate
        
    etf_values_czk = []
    etf_cashflows_arr = [-initial_investment]
    
    # Helper to handle scalar vs array inputs (for Monte Carlo compatibility)
    def get_rate(rate_input, year_index):
        if isinstance(rate_input, (list, np.ndarray)):
            if year_index < len(rate_input):
                return rate_input[year_index]
            return rate_input[-1]
        return rate_input
        
    tax_y1 = 0

    # MAIN LOOP
    # Ensure holding_period is an integer
    holding_period = int(holding_period)
    
    for year in range(1, holding_period + 1):
        year_idx = year - 1
        
        # a) Property Appreciation
        rate_app = get_rate(appreciation_rate, year_idx)
        current_property_value *= (1 + rate_app / 100)
        property_values.append(current_property_value)
        
        # b) Rent & Expenses Inflation
        rate_rent = get_rate(rent_growth_rate, year_idx)
        curr_annual_gross_rent *= (1 + rate_rent / 100)
        curr_annual_expenses *= (1 + rate_rent / 100)
        
        # c) Interest Payment Calculation (Approximate for Tax)
        # Interest part of payment changes every month, but for annual sum we approximate
        # Interest ~ Balance * Rate
        interest_paid_this_year = current_mortgage_balance * (interest_rate / 100)
        
        # Tax Calculation
        # Základ daně = Příjem - Výdaje - Úroky (zjednodušeně, bez odpisů nemovitosti, což je konzervativní)
        taxable_income = curr_annual_gross_rent - curr_annual_expenses - interest_paid_this_year
        tax_paid = max(0, taxable_income * (tax_rate / 100))
        
        if year == 1:
            tax_y1 = tax_paid
        
        # Net Cashflow
        curr_annual_cf = curr_annual_gross_rent - annual_mortgage_payment - curr_annual_expenses - tax_paid
        operating_cashflows.append(curr_annual_cf)
        
        yearly_cashflows_arr.append(curr_annual_cf)
        
        # d) Mortgage Balance Update - Delegated to logic/finance
        current_mortgage_balance = update_remaining_balance(
            current_mortgage_balance, monthly_rate, monthly_mortgage_payment
        )
        mortgage_balances.append(current_mortgage_balance)
        
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
            
            # Value update at end of year
            current_fx_rate_end = initial_fx_rate * ((1 + fx_appreciation / 100) ** year)
            etf_value_now_czk = etf_balance_eur * current_fx_rate_end
            etf_values_czk.append(etf_value_now_czk)
            etf_cashflows_arr.append(-year_contribution_czk)
    
    # Results
    sale_price = property_values[-1]
    final_mortgage_balance = mortgage_balances[-1]
    
    # 1. Sale Transaction Costs (e.g., Real Estate Agent fee)
    sale_costs = sale_price * (sale_fee_percent / 100.0)
    
    # 2. Capital Gains Tax
    # Taxable Base = Sale Price - Purchase Price - Improvements(One-off) - Sale Costs
    # Note: Purchase price is static here, assuming no capital improvements in between
    taxable_gain = sale_price - purchase_price - one_off_costs - sale_costs
    
    capital_gains_tax = 0
    if taxable_gain > 0:
        is_exempt = False
        if time_test_vars['enabled']:
            # Check time test (e.g. 10 years for CZ)
            if holding_period > time_test_vars['years']:
                is_exempt = True
        
        if not is_exempt:
            capital_gains_tax = taxable_gain * (tax_rate / 100)
            
    net_proceeds = sale_price - final_mortgage_balance - sale_costs - capital_gains_tax
    
    # FINAL CASHFLOW for IRR
    yearly_cashflows_arr[-1] += net_proceeds
    
    total_profit = sum(yearly_cashflows_arr)
    
    # IRR Calculation
    try:
        irr = npf.irr(yearly_cashflows_arr) * 100
        if np.isnan(irr): irr = 0
    except:
        irr = 0
        
    # ETF Output
    etf_irr = 0
    final_etf_value_czk = 0
    if etf_comparison:
        final_etf_value_czk = etf_values_czk[-1]
        etf_cashflows_arr[-1] += final_etf_value_czk
        try:
            etf_irr = npf.irr(etf_cashflows_arr) * 100
            if np.isnan(etf_irr): etf_irr = 0
        except:
            etf_irr = 0
            
    # --- Real Values (Inflation Adjusted) ---
    real_property_values = []
    real_operating_cashflows = []
    real_mortgage_balances = []
    real_etf_values = []
    
    for i, year in enumerate(range(1, int(holding_period) + 1)):
        # Determine strict inflation rate (scalar)
        inf_rate = general_inflation_rate
        if isinstance(general_inflation_rate, (list, np.ndarray)):
             inf_rate = np.mean(general_inflation_rate) # Fallback for MC
             
        df = (1 + inf_rate / 100) ** year
        
        real_property_values.append(property_values[i] / df)
        real_operating_cashflows.append(operating_cashflows[i] / df)
        real_mortgage_balances.append(mortgage_balances[i] / df)
        
        if etf_comparison and i < len(etf_values_czk):
             real_etf_values.append(etf_values_czk[i] / df)
        else:
             real_etf_values.append(0)
    
    return {
        "irr": irr,
        "total_profit": total_profit,
        "etf_irr": etf_irr,
        "monthly_cashflow_y1": annual_cashflow_year1 / 12,
        "tax_paid_y1": tax_y1,
        "capital_gains_tax": capital_gains_tax,
        "initial_investment": initial_investment,
        "initial_mortgage": mortgage_amount,
        "series": {
            "property_values": property_values,
            "mortgage_balances": mortgage_balances,
            "operating_cashflows": operating_cashflows,
            "cashflows": yearly_cashflows_arr,
            "etf_values": etf_values_czk,
            "etf_cashflows": etf_cashflows_arr,
            "real_property_values": real_property_values,
            "real_mortgage_balances": real_mortgage_balances,
            "real_operating_cashflows": real_operating_cashflows,
            "real_etf_values": real_etf_values
        }
    }

# Forwarding functions to new logic modules
def calculate_marginal_roe(*args, **kwargs):
    return strategy.calculate_marginal_roe(*args, **kwargs)

def project_future_wealth(*args, **kwargs):
    return strategy.project_future_wealth(*args, **kwargs)

def calculate_decision_metrics_for_price(*args, **kwargs):
    return strategy.calculate_decision_metrics_for_price(*args, **kwargs)

def run_monte_carlo(*args, **kwargs):
    return monte_carlo.run_monte_carlo(*args, **kwargs)
