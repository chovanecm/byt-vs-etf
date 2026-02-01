import streamlit as st
import pandas as pd

def render_cashflow_tab(inputs, metrics, derived_metrics):
    holding_period = inputs['holding_period']
    etf_comparison = inputs['etf_comparison']
    show_real = inputs.get('show_real_values', False)
    
    if show_real:
        property_values = metrics['series']['real_property_values']
        mortgage_balances = metrics['series']['real_mortgage_balances']
        etf_values_czk = metrics['series']['real_etf_values']
        
        # Use pre-calculated real cashflows series from calculations.py
        yearly_cashflows_arr = metrics['series'].get('real_cashflows')
        
        # Fallback if logic mismatch (e.g. key missing in old state)
        if not yearly_cashflows_arr:
            inf_rate = inputs.get('general_inflation_rate', 2.0)
            nominal_cfs = metrics['series']['cashflows']
            yearly_cashflows_arr = [nominal_cfs[0]] + [nominal_cfs[i] / ((1 + inf_rate/100)**i) for i in range(1, len(nominal_cfs))]

        equity_values = [p - m for p, m in zip(property_values, mortgage_balances)]
        
        st.info(f"ℹ️ Zobrazeno v **REÁLNÝCH CENÁCH** (očištěno o inflaci {inputs.get('general_inflation_rate', 2.0)}% p.a.).")
    else:
        property_values = metrics['series']['property_values']
        mortgage_balances = metrics['series']['mortgage_balances']
        yearly_cashflows_arr = metrics['series']['cashflows']
        etf_values_czk = metrics['series']['etf_values']
        equity_values = derived_metrics['equity_values']

    etf_cashflows_arr = metrics['series']['etf_cashflows'] # This we handle inside ETF logic below if needed
    
    st.subheader("Detailní roční cashflow")
    
    # Vytvoření detailní tabulky
    data_dict = {
        "Rok": range(1, holding_period + 1),
        "Nemovitost Hodnota": [int(x) for x in property_values],
        "Dluh": [int(x) for x in mortgage_balances],
        "Equity": [int(x) for x in equity_values],
        "Roční CF Nemovitost": [int(x) for x in yearly_cashflows_arr[1:holding_period+1]] # Bez finálního prodeje pro přehlednost? Ne, yearly_cashflows_arr[-1] má v sobě prodej.
    }
    
    # Oprava zobrazení CF v posledním roce (chceme vidět provozní CF, ne s prodejem v tabulce cashflow?)
    # Pro tabulku je lepší vidět provozní data. year_cashflow_arr je pro IRR.
    # Musíme rekonstruovat provozní CF pro poslední rok.
    # Ale uživatel chce vidět data.
    
    df_detail = pd.DataFrame(data_dict)
    
    final_etf_value_czk = 0
    if len(etf_values_czk) > 0:
        final_etf_value_czk = etf_values_czk[-1]

    if etf_comparison:
        df_detail["ETF Hodnota (CZK)"] = [int(x) for x in etf_values_czk]
        # Přidat sloupec s investicí do ETF (Reinvestice)
        # Rekonstrukce z etf_cashflows_arr: [1:] jsou roční vklady (záporné).
        # Pozor: poslední prvek etf_cashflows_arr má přičtenou finální hodnotu.
        
        etf_investments = [-int(x) for x in etf_cashflows_arr[1:-1]] # Vše mezi 0 a -1
        # Poslední rok
        last_flow = etf_cashflows_arr[-1] - final_etf_value_czk # Odečteme finální hodnotu abychom dostali jen vklad
        etf_investments.append(-int(last_flow))
        
        df_detail["ETF Vklad (DCA)"] = etf_investments

    st.dataframe(df_detail, use_container_width=True)
    
    # Download button
    csv = df_detail.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Stáhnout data (CSV)",
        csv,
        "investice_data.csv",
        "text/csv"
    )
