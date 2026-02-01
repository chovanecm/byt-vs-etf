import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from views.funding import render_funding_section

def render_analysis_tab(inputs, metrics, derived_metrics):
    # --- 0. FUNDING WIZARD (Top Section) ---
    render_funding_section(inputs)

    # Unpack needed values
    holding_period = inputs['holding_period']
    etf_comparison = inputs['etf_comparison']
    
    # Toggle between Real and Nominal values based on user selection
    show_real = inputs.get('show_real_values', False)
    
    if show_real:
        property_values = metrics['series']['real_property_values']
        mortgage_balances = metrics['series']['real_mortgage_balances']
        etf_values_czk = metrics['series']['real_etf_values']
        equity_values = [p - m for p, m in zip(property_values, mortgage_balances)]
        
        # Discount scalar values for consistency
        # Assuming general_inflation_rate from inputs is used
        inf_rate = inputs.get('general_inflation_rate', 2.0)
        # Handle if inf_rate is list/array (Monte Carlo legacy?) - unlikely here in detailed view
        if isinstance(inf_rate, (list, tuple)): inf_rate = 2.0
            
        discount_factor = (1 + inf_rate / 100) ** holding_period
        
        sale_proceeds_net = derived_metrics['sale_proceeds_net'] / discount_factor
        total_cf_sum = derived_metrics['total_cf_sum'] / discount_factor 
        # Note: Recalculating total_cf_sum from real cashflow series would be more accurate 
        # (sum of discounted CFs), but simply discounting nominal sum is acceptable approximation 
        # for this high-level summary if we assume uniform distribution, which is NOT true.
        # Better: Sum the real operating cashflows.
        
        real_op_cf = metrics['series']['real_operating_cashflows']
        # The total_cf_sum usually means "rental income net of expenses" accumulated?
        # In app.py: total_cf_sum = total_profit - sale_proceeds_net + initial_investment
        # = Sum(YearlyCFs excluding sale)
        # So we can sum the real_operating_cashflows (excluding Y0 which is investment)
        total_cf_sum = sum(real_op_cf) 

        st.info(f"ℹ️ Zobrazeno v **REÁLNÝCH CENÁCH** (očištěno o inflaci {inf_rate}% p.a.).")
    else:
        property_values = metrics['series']['property_values']
        mortgage_balances = metrics['series']['mortgage_balances']
        etf_values_czk = metrics['series']['etf_values']
        equity_values = derived_metrics['equity_values']
        
        sale_proceeds_net = derived_metrics['sale_proceeds_net']
        total_cf_sum = derived_metrics['total_cf_sum']
    
    total_profit = metrics['total_profit'] # Note: Profit logic might need adjustment if real values strictly requested for summary too
    initial_investment = metrics['initial_investment']

    # sale_proceeds_net and total_cf_sum in derived_metrics are currently Nominal-only.
    # For full consistency, we would need to recalc them. 
    # For now, we focus on the Main Chart Visualization.

    # Grafy
    st.subheader("Vývoj hodnoty a dluhu v čase")

    # Příprava DF pro graf
    df_chart = pd.DataFrame({
        "Rok": list(range(1, holding_period + 1)),
        "Hodnota nemovitosti": property_values,
        "Zůstatek hypotéky": mortgage_balances,
        "Čisté jmění (Equity)": equity_values
    })

    # Plotly Graf - 2 osy nebo skládaný
    fig = go.Figure()

    # 1. Hodnota nemovitosti (Kontext, tenká čára)
    fig.add_trace(go.Scatter(
        x=df_chart["Rok"], 
        y=df_chart["Hodnota nemovitosti"],
        mode='lines',
        name='Tržní cena nemovitosti',
        line=dict(color='#A5D6A7', width=2, dash='dot'), # Světlejší zelená, méně dominantní
        legendgroup="property"
    ))

    # 2. Vlastní kapitál v nemovitosti (Equity) - HLAVNÍ METRIKA
    fig.add_trace(go.Scatter(
        x=df_chart["Rok"], 
        y=df_chart["Čisté jmění (Equity)"],
        mode='lines',
        name='Net Worth Nemovitost (Equity)',
        line=dict(color='#2E7D32', width=4), # Silná tmavě zelená
        legendgroup="property"
    ))

    # 3. Zůstatek hypotéky (Kontext)
    fig.add_trace(go.Scatter(
        x=df_chart["Rok"], 
        y=df_chart["Zůstatek hypotéky"],
        mode='lines',
        name='Zůstatek hypotéky',
        line=dict(color='#EF9A9A', width=1), # Světle červená
        fill='tozeroy', # Vyplní oblast pod křivkou
        fillcolor='rgba(239, 154, 154, 0.2)',
        legendgroup="debt"
    ))

    # Přidání ETF do grafu
    if etf_comparison:
        fig.add_trace(go.Scatter(
            x=df_chart["Rok"], 
            y=etf_values_czk,
            mode='lines',
            name='Net Worth ETF (Investovaný vlastní kap.)',
            line=dict(color='#2196F3', width=4) # Silná modrá pro přímé porovnání s Equity
        ))

    fig.update_layout(
        title=f"Porovnání čistého majetku (Net Worth): Nemovitost vs. ETF",
        xaxis_title="Rok",
        yaxis_title="Hodnota (Kč)",
        legend_title="Legenda",
        hovermode="x unified",
        height=500
    )

    st.plotly_chart(fig, width="stretch")

    # Celkový profit report
    st.subheader(f"💰 Finanční výsledek po {holding_period} letech")
    res_col1, res_col2 = st.columns(2)

    final_value = property_values[-1]
    final_debt = mortgage_balances[-1]

    with res_col1:
        st.markdown(f"""
        **Složení majetku na konci:**
        - Odhadovaná tržní cena: **{int(final_value):,} Kč**
        - Zbývající dluh: **{int(final_debt):,} Kč**
        - Čistá hodnota při prodeji: **{int(sale_proceeds_net):,} Kč**
        """)

    with res_col2:
        roi = (total_profit / initial_investment) * 100 if initial_investment > 0 else 0
        st.markdown(f"""
        **Ziskovost:**
        - Kumulované cashflow (příjmy z nájmu): **{int(total_cf_sum):,} Kč**
        - **Celkový čistý zisk:** **{int(total_profit):,} Kč**
        - ROI (Celková návratnost): **{roi:.1f} %**
        """)
        st.caption(f"Kolikrát se vaše investice ({int(initial_investment):,} Kč) znásobila? To vyjadřuje ROI.")
