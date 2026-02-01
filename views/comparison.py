import streamlit as st
import pandas as pd

def render_comparison_tab(inputs, metrics, derived_metrics):
    etf_comparison = inputs['etf_comparison']
    initial_investment = metrics['initial_investment']
    irr = metrics['irr']
    total_profit = metrics['total_profit']
    etf_irr = metrics['etf_irr']
    
    yearly_cashflows_arr = metrics['series']['cashflows']
    holding_period = inputs['holding_period']
    etf_total_invested_czk = derived_metrics['etf_total_invested_czk']
    etf_profit = derived_metrics['etf_profit']
    etf_roi = derived_metrics['etf_roi']
    sale_proceeds_net = derived_metrics['sale_proceeds_net']
    final_etf_value_czk = derived_metrics['final_etf_value_czk']
    
    roi = derived_metrics['roi']

    # Detailní porovnání v tabulce
    if etf_comparison:
        st.subheader("⚖️ Porovnání: Nemovitost vs. ETF")
        
        comp_col1, comp_col2, comp_col3 = st.columns(3)
        
        with comp_col1:
            st.metric(label="🏢 IRR Nemovitost", value=f"{irr:.2f} %")
            st.caption(f"Celkový zisk: {int(total_profit):,} Kč")
        
        with comp_col2:
            st.metric(label="📈 IRR ETF (IWDA)", value=f"{etf_irr:.2f} %")
            st.caption(f"Celkový zisk: {int(etf_profit):,} Kč")
        
        with comp_col3:
            diff = irr - etf_irr
            delta_color = "normal" if diff > 0 else "inverse"
            st.metric(label="Rozdíl IRR", value=f"{diff:.2f} p.p.", delta=f"{diff:.2f} p.p.", delta_color=delta_color)
            winner = "Nemovitost" if diff > 0 else "ETF"
            st.caption(f"Lepší: {winner}")
        
        st.warning(f"""
        **📌 Metodika srovnání:** Pokud nemovitost generuje záporné cashflow (nájem nepokryje splátku a náklady), 
        model předpokládá, že v ETF scénáři by investor tuto částku ("dotaci") pravidelně investoval do ETF (DCA strategie).
        
        **Investováno do ETF navíc:** {int(etf_total_invested_czk - initial_investment):,} Kč (Suma měsíčních dotací za {holding_period} let).
        """)
        
        st.divider()
        st.subheader("📋 Detailní srovnání parametrů")
        
        comparison_data = {
            "Metrika": [
                "Počáteční investice (Hotovost)",
                "Celkem investováno (vč. dotací)",
                "Konečná hodnota",
                "Čistý zisk",
                "ROI celkem (%)",
                "IRR roční (%)",
                "Rizikový profil"
            ],
            "Nemovitost 🏢": [
                f"{int(initial_investment):,} Kč",
                f"{int(initial_investment + abs(sum(x for x in yearly_cashflows_arr if x < 0)) - initial_investment):,} Kč", # Zjednodušený odhad invested
                f"{int(sale_proceeds_net):,} Kč",
                f"{int(total_profit):,} Kč",
                f"{roi:.1f} %",
                f"{irr:.2f} %",
                "Páka, neobsazenost, lokální trh"
            ],
            "ETF (IWDA) 📈": [
                f"{int(initial_investment):,} Kč",
                f"{int(etf_total_invested_czk):,} Kč",
                f"{int(final_etf_value_czk):,} Kč",
                f"{int(etf_profit):,} Kč",
                f"{etf_roi:.1f} %",
                f"{etf_irr:.2f} %",
                "Likvidní, FX riziko, diverzifikované"
            ]
        }
        
        df_comparison = pd.DataFrame(comparison_data)
        st.table(df_comparison)
    else:
        st.info("Pro zobrazení porovnání zapněte možnost 'Porovnat s ETF' v levém panelu v sekci 'Alternativní investice'.")
