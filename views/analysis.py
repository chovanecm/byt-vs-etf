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
    
    property_values = metrics['series']['property_values']
    mortgage_balances = metrics['series']['mortgage_balances']
    total_profit = metrics['total_profit']
    initial_investment = metrics['initial_investment']
    
    etf_values_czk = metrics['series']['etf_values']
    
    equity_values = derived_metrics['equity_values']
    sale_proceeds_net = derived_metrics['sale_proceeds_net']
    total_cf_sum = derived_metrics['total_cf_sum']

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
