import numpy_financial as npf
import numpy as np
import pandas as pd

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
    operating_cashflows = []
    
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
        operating_cashflows.append(curr_annual_cf)
        
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
        "initial_mortgage": mortgage_amount,
        "series": {
            "property_values": property_values,
            "mortgage_balances": mortgage_balances,
            "operating_cashflows": operating_cashflows,
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

def calculate_marginal_roe(
    metrics,
    purchase_price,
    one_off_costs,
    sale_fee_percent,
    tax_rate,
    time_test_vars,
    etf_return_rate,
    interest_rate_current, # Rate of existing mortgage
    market_refinance_rate,  # New rate if we refinance
    target_ltv_refinance    # Desired LTV for refinance
):
    """
    Vypočítá meziroční metriky (Marginal ROE) a simulace.
    Vrací DataFrame s ročními daty.
    """
    import pandas as pd
    
    series = metrics['series']
    prop_values = series['property_values']
    mtg_balances = series['mortgage_balances']
    op_cashflows = series['operating_cashflows']
    initial_mortgage = metrics['initial_mortgage']
    
    years = []
    annual_roes = []
    equity_starts = []
    net_equities = [] # Čistá hodnota při prodeji (po zdanění a poplatcích)
    ref_cashouts = []
    ref_benefits = [] # Čistý roční přínos refinancování v CZK

    num_years = len(prop_values)
    
    for i in range(num_years):
        year = i + 1
        years.append(year)
        
        # 1. Start & End values
        if year == 1:
            val_start = purchase_price
            mtg_start = initial_mortgage
        else:
            val_start = prop_values[i-1]
            mtg_start = mtg_balances[i-1]
            
        val_end = prop_values[i]
        mtg_end = mtg_balances[i]
        
        # 2. Components of Return for ROE
        appreciation = val_end - val_start
        principal_paydown = mtg_start - mtg_end
        cashflow = op_cashflows[i]
        
        total_gain = appreciation + principal_paydown + cashflow
        
        # 3. Equity Basis (Start of Year)
        equity_start = val_start - mtg_start
        equity_starts.append(equity_start)
        
        # 4. ROE Calculation
        if equity_start > 1000: # Defensive
            roe = (total_gain / equity_start) * 100
        else:
            roe = 0 
        annual_roes.append(roe)
        
        # 5. Net Equity (Liquidation Value at End of Year)
        sale_costs = val_end * (sale_fee_percent / 100.0)
        
        # Capital Gains Tax Logic
        capital_gains_tax = 0
        if time_test_vars and time_test_vars.get("enabled", True):
            limit_years = time_test_vars.get("years", 10)
            if year < limit_years:
                total_acq_cost = purchase_price + one_off_costs
                profit = val_end - sale_costs - total_acq_cost
                if profit > 0:
                    capital_gains_tax = profit * (tax_rate / 100.0)
        
        net_equity = val_end - mtg_end - sale_costs - capital_gains_tax
        net_equities.append(net_equity)
        
        # 6. Refinance Potential (User Defined LTV)
        # New Loan Amount
        max_loan_amount = val_end * (target_ltv_refinance / 100.0)
        potential_cash_out = max_loan_amount - mtg_end
        cash_out = max(0, potential_cash_out)
        ref_cashouts.append(cash_out)
        
        # 7. Refinance Arbitrage (Complex Cost Analysis)
        # Situation A (Keep): Pay Interest on Old Debt only
        cost_keep = mtg_end * (interest_rate_current / 100.0)
        
        # Situation B (Refinance): Pay Interest on New Total Debt (Old + CashOut) at NEW Rate
        # Assumption: Banks usually reprice the whole debt effectively
        cost_refinance = max_loan_amount * (market_refinance_rate / 100.0)
        
        # Income from CashOut invested in ETF
        income_etf = cash_out * (etf_return_rate / 100.0)
        
        # Net Benefit = (Income_ETF) - (Difference in Interest Costs)
        # Benefit = Income_ETF - (Cost_Refinance - Cost_Keep)
        increased_interest_cost = cost_refinance - cost_keep
        benefit = income_etf - increased_interest_cost
        
        ref_benefits.append(benefit)

    df = pd.DataFrame({
        'Year': years,
        'Marginal_ROE': annual_roes,
        'Equity_Start': equity_starts,
        'Net_Liquidation_Value': net_equities,
        'Refinance_CashOut': ref_cashouts,
        'Refinance_Arbitrage_CZK': ref_benefits,
        'ETF_Benchmark': [etf_return_rate] * num_years
    })
    
    # Opportunity Cost Sim: "Dead Equity Gap"
    df['Gap'] = df['ETF_Benchmark'] - df['Marginal_ROE']
    
    return df

def calculate_decision_metrics_for_price(
    property_value,
    mortgage_balance,
    purchase_price,
    one_off_costs,
    sale_fee_percent,
    tax_rate,
    time_test_vars,
    holding_years,
    target_ltv_ref,
    market_ref_rate,
    interest_rate_current,
    etf_return_rate
):
    """
    Vypočítá rozhodovací metriky (Net Equity, Refinance Benefit) pro konkrétní zadanou cenu.
    Používá se pro manuální override ceny v UI.
    """
    # 1. Net Equity (Self calculation)
    sale_costs = property_value * (sale_fee_percent / 100.0)
    
    capital_gains_tax = 0
    if time_test_vars and time_test_vars.get("enabled", True):
        limit_years = time_test_vars.get("years", 10)
        if holding_years < limit_years:
            total_acq_cost = purchase_price + one_off_costs
            profit = property_value - sale_costs - total_acq_cost
            if profit > 0:
                capital_gains_tax = profit * (tax_rate / 100.0)
            
    net_equity = property_value - mortgage_balance - sale_costs - capital_gains_tax
    
    # 2. Refinance Analysis
    max_loan_amount = property_value * (target_ltv_ref / 100.0)
    potential_cash_out = max_loan_amount - mortgage_balance
    cash_out = max(0, potential_cash_out)
    
    # Arbitrage
    cost_keep = mortgage_balance * (interest_rate_current / 100.0)
    cost_refinance = max_loan_amount * (market_ref_rate / 100.0)
    income_etf = cash_out * (etf_return_rate / 100.0)
    
    benefit = income_etf - (cost_refinance - cost_keep)
    
    return {
        "Net_Liquidation_Value": net_equity,
        "Refinance_CashOut": cash_out,
        "Refinance_Arbitrage_CZK": benefit
    }

def project_future_wealth(
    start_property_value,
    start_mortgage_balance,
    net_liquidation_value,
    monthly_payment,
    mortgage_rate,
    appreciation_rate,
    etf_return_rate,
    projection_years=10
):
    """
    Porovná vývoj majetku (Net Worth) pro dvě strategie:
    A) HOLD: Držet nemovitost dalších X let
    B) SELL: Prodat, zaplatit daně/poplatky (Net_Liquidation_Value) a investovat do ETF
    """
    import pandas as pd
    import numpy_financial as npf

    years = []
    nw_hold = []
    nw_sell = []
    
    # Setup - Scenario A (HOLD)
    curr_val = start_property_value
    curr_mtg = start_mortgage_balance
    monthly_rate = (mortgage_rate / 100) / 12
    
    # Setup - Scenario B (SELL)
    # Start with cash generated from sale
    curr_etf_balance = net_liquidation_value
    
    for y in range(1, projection_years + 1):
        years.append(y)
        
        # --- A: HOLD strategy ---
        # 1. Růst ceny
        curr_val *= (1 + appreciation_rate / 100)
        
        # 2. Splácení hypotéky (12 měsíců)
        if curr_mtg > 0:
            # FV konvence: rate, nper, pmt, pv
            # pv = -dluh (negativní cashflow na začátku z pohledu dluhu? ne, dluh je závazek)
            # Konvence npf.fv: 
            # Pokud úrok > 0: dluh roste. Splátka dluh snižuje.
            # FV(rate, n, pmt, -principal)
            # Pokud principal=1M, pmt=0 -> FV = 1M * (1+r)^n (dluh roste)
            # Pokud pmt > 0 -> snižuje dluh.
            # Zůstatek hypotéky by měl být kladné číslo (velikost dluhu).
            # Použijeme logiku: Zůstatek = FV(rate, 12, pmt, -curr_mtg)
            # Výsledek bude kladný (zbytek dluhu), pokud jsme nesplatili vše.
            res = npf.fv(monthly_rate, 12, monthly_payment, -curr_mtg)
            curr_mtg = res
            
            # Pokud je výsledek záporný (přeplatek?), dluh je 0.
            # FV convention: PV=-Debt. FV=+RemainingDebt.
            # If we overpay (PMT very high), FV becomes larger positive? 
            # No. PV+PMT+FV=0. -100 + 200 + FV = 0 -> FV = -100.
            # So if we overpay, FV becomes negative.
            if curr_mtg < 0: curr_mtg = 0
            
        equity_hold = curr_val - curr_mtg
        nw_hold.append(equity_hold)
        
        # --- B: SELL strategy ---
        # Jednoduché úročení ETF
        curr_etf_balance *= (1 + etf_return_rate / 100)
        nw_sell.append(curr_etf_balance)
        
    return pd.DataFrame({
        "Year_Relative": years,
        "NW_Hold": nw_hold,
        "NW_Sell": nw_sell
    })
