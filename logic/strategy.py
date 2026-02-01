import pandas as pd
import numpy_financial as npf
import numpy as np

def calculate_marginal_roe(
    metrics,
    purchase_price,
    one_off_costs,
    sale_fee_percent,
    tax_rate,
    time_test_vars,
    etf_return_rate,
    interest_rate_current, 
    market_refinance_rate,
    target_ltv_refinance
):
    """
    Vypočítá meziroční metriky (Marginal ROE) a rozhodovací tabulku.
    Refaktorovaná logika pro Strategy View.
    """
    series = metrics['series']
    prop_values = series['property_values']
    mtg_balances = series['mortgage_balances']
    op_cashflows = series['operating_cashflows']
    
    # Check for real vs nominal inputs in metrics (if available) - standard is nominal here
    
    years = []
    
    for i in range(len(prop_values)):
        year = i + 1
        
        # 1. Aktuální stav na konci roku
        market_val = prop_values[i]
        debt = mtg_balances[i]
        
        # 2. Net Liquidation Value (Kdybych dnes prodal)
        # Poplatky z prodeje
        sale_fee = market_val * (sale_fee_percent / 100.0)
        
        # Daň z prodeje
        taxable_gain = market_val - purchase_price - one_off_costs - sale_fee
        
        capital_gains_tax = 0
        if taxable_gain > 0:
            exempt = False
            if time_test_vars['enabled']:
                if year > time_test_vars['years']:
                    exempt = True
            
            if not exempt:
                capital_gains_tax = taxable_gain * (tax_rate / 100.0)

        net_equity = market_val - debt - sale_fee - capital_gains_tax
        
        # 3. Změna Equity pro další rok (Marginal Return)
        # Potřebujeme predikci na rok +1
        if i < len(prop_values) - 1:
            next_val = prop_values[i+1]
            next_debt = mtg_balances[i+1]
            next_cf = op_cashflows[i+1] # Cashflow během roku T+1
            
            # Další rok Exit
            sale_fee_next = next_val * (sale_fee_percent / 100.0)
            taxable_gain_next = next_val - purchase_price - one_off_costs - sale_fee_next
            
            cap_tax_next = 0
            if taxable_gain_next > 0:
                exempt_next = False
                if time_test_vars['enabled']:
                    if (year + 1) > time_test_vars['years']:
                        exempt_next = True
                if not exempt_next:
                    cap_tax_next = taxable_gain_next * (tax_rate / 100.0)
            
            net_equity_next = next_val - next_debt - sale_fee_next - cap_tax_next
            
            # Zisk z držení = (Equity T+1 - Equity T) + Cashflow T+1
            profit_hold = (net_equity_next - net_equity) + next_cf
            
            # Marginal ROE = Zisk / Investovaná Equity (neboli Equity T)
            if net_equity > 0:
                marg_roe = (profit_hold / net_equity) * 100
            else:
                marg_roe = 0 # Distress scenario
        else:
            marg_roe = 0 # No data for next year
            
        # 4. Opportunity Cost (ETF)
        # Porovnáváme s fixním vstupem nebo dynamicky? Zde fixní vstup 'etf_return_rate'
        
        # Gap
        gap = marg_roe - etf_return_rate
        
        years.append({
            "Year": year,
            "Market_Value": market_val,
            "Debt": debt,
            "Net_Equity": net_equity, # "Uvězněné peníze"
            "Marginal_ROE": marg_roe,
            "ETF_Benchmark": etf_return_rate,
            "Gap": gap
        })
        
    return pd.DataFrame(years)


def project_future_wealth(
    start_property_value,
    start_mortgage_balance,
    net_liquidation_value, # Cash if sold today (Initial ETF investment)
    monthly_payment,
    mortgage_rate, # Nominal
    appreciation_rate,
    etf_return_rate,
    projection_years=10
):
    """
    Projekce čistého majetku (Net Worth) pro dvě cesty:
    A) HOLD: Držím nemovitost dál
    B) SELL: Prodám, zaplatím daně/poplatky, zbytek do ETF
    """
    
    # Init vectors
    nw_hold = []
    nw_sell = [] # ETF strategy matches benchmark
    
    # Current State
    curr_val = start_property_value
    curr_debt = start_mortgage_balance
    
    # ETF State
    curr_etf = net_liquidation_value
    
    for y in range(1, projection_years + 1):
        # --- A) HOLD PATH ---
        # 1. Appreciation
        curr_val *= (1 + appreciation_rate / 100.0)
        
        # 2. Debt Paydown (Approx)
        # Using simple FV for principal reduction
        monthly_r = (mortgage_rate / 100.0) / 12
        if curr_debt > 0:
            curr_debt = npf.fv(monthly_r, 12, monthly_payment, -curr_debt)
            if curr_debt < 0: curr_debt = 0
            
        # 3. Cashflow accumulation? 
        # For simplicity, Strategy Projection usually focuses on Asset Growth vs Asset Growth
        # ignoring accumulated rental cashflow vs reinvested dividends diff, 
        # unless we want perfect accuracy. 
        # Let's assume Rental Cashflow ~= 0 or consumed, to KISS. 
        # OR: Add rental yield? 
        # Let's stick to Asset Value - Debt for NW.
        
        equity_hold = curr_val - curr_debt
        nw_hold.append(equity_hold)
        
        # --- B) SELL PATH ---
        curr_etf *= (1 + etf_return_rate / 100.0)
        nw_sell.append(curr_etf)
        
    return pd.DataFrame({
        "Year_Relative": list(range(1, projection_years + 1)),
        "NW_Hold": nw_hold,
        "NW_Sell": nw_sell
    })

def calculate_decision_metrics_for_price(
    property_value,
    mortgage_balance,
    purchase_price,
    one_off_costs,
    sale_fee_percent,
    tax_rate,
    time_test_vars,
    holding_years,
    etf_return_rate,
    interest_rate_current,
    market_ref_rate,
    target_ltv_ref
):
    """
    Vypočítá jednorázové metriky pro daný rok a danou (možná přepsanou) cenu nemovitosti.
    Slouží pro interaktivní karty ve Strategii.
    """
    
    # 1. SELL SCENARIO
    sale_fee = property_value * (sale_fee_percent / 100.0)
    taxable_gain = property_value - purchase_price - one_off_costs - sale_fee
    
    cap_tax = 0
    if taxable_gain > 0:
        exempt = False
        if time_test_vars['enabled'] and holding_years > time_test_vars['years']:
            exempt = True
        
        if not exempt:
            cap_tax = taxable_gain * (tax_rate / 100.0)
            
    net_liquidation_value = property_value - mortgage_balance - sale_fee - cap_tax
    
    # 2. REFINANCE SCENARIO
    # Nová výše úvěru
    new_loan_amount = property_value * (target_ltv_ref / 100.0)
    
    # Cash Out
    # Kolik splatím starého?
    old_loan_to_pay = mortgage_balance
    
    cash_out = new_loan_amount - old_loan_to_pay
    # Pokud je nová hypotéka nižší než stávající dluh, cash_out je záporný (musím doplatit) -> v praxi nerealizovatelné jako "výběr zisku"
    
    # Arbitrážní profit
    # Získaný Cash Out investuji za etf_return_rate
    # Ale platím z něj úrok (market_ref_rate)
    # Rozdíl = CashOut * (InvestReturn - CostOfDebt)
    # POZOR: Daňový štít úroků hypotéky vs Zdanění výnosů ETF.
    # Pro jednoduchost Hrubý vs Hrubý.
    
    spread = etf_return_rate - market_ref_rate
    arbitrage_annual = cash_out * (spread / 100.0)
    
    return {
        "Net_Liquidation_Value": net_liquidation_value,
        "Refinance_CashOut": cash_out,
        "Refinance_Arbitrage_CZK": arbitrage_annual, # Roční efekt
        "Potential_Tax": cap_tax
    }
