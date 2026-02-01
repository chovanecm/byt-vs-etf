import streamlit as st
import pandas as pd
import calculations
import altair as alt

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
    
    show_real = inputs.get('show_real_values', False)
    if show_real:
        inf_rate = inputs.get('general_inflation_rate', 2.0)
        df_final = (1 + inf_rate / 100) ** holding_period
        
        # Use pre-calculated real total profit if available
        total_profit = metrics.get('real_total_profit')
        if total_profit is None:
             # Fallback
             nominal_cfs = metrics['series']['cashflows']
             real_cfs = [nominal_cfs[0]] + [nominal_cfs[i] / ((1 + inf_rate/100)**i) for i in range(1, len(nominal_cfs))]
             total_profit = sum(real_cfs)
        
        sale_proceeds_net = sale_proceeds_net / df_final
        final_etf_value_czk = metrics['series']['real_etf_values'][-1] if metrics['series']['real_etf_values'] else 0
        
        # Recalc ETF invested sum from discounted flows
        etf_flows = metrics['series']['etf_cashflows']
        # Real ETF Flows (recalc on spot as it is specific to this view's breakdown)
        real_etf_flows = [etf_flows[i] / ((1 + inf_rate/100)**i) for i in range(len(etf_flows))]
        # Invested is sum of negative flows (excluding last)
        real_invested_sum = sum([-f for f in real_etf_flows if f < 0])
        etf_total_invested_czk = real_invested_sum
        etf_profit = final_etf_value_czk - etf_total_invested_czk
        
        st.info(f"ℹ️ Zobrazeno v **REÁLNÝCH CENÁCH** (očištěno o inflaci {inf_rate}% p.a.).")
    else:
        # Default nominal
        pass

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
        
        st.divider()
        st.subheader("🔍 Opportunity Cost: Kdy prodat?")
        st.info("👉 Podrobnou analýzu Opportunity Cost a strategie prodeje v čase najdete nyní na záložce **Strategie**.")
            
    else:
        st.info("Pro zobrazení porovnání zapněte možnost 'Porovnat s ETF' v levém panelu v sekci 'Adv. / Opportunity Cost'.")
