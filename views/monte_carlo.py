import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calculations

def render_monte_carlo_tab(inputs):
    etf_comparison = inputs['etf_comparison']
    purchase_price = inputs['purchase_price']
    down_payment = inputs['down_payment']
    one_off_costs = inputs['one_off_costs']
    interest_rate = inputs['interest_rate']
    loan_term_years = inputs['loan_term_years']
    monthly_rent = inputs['monthly_rent']
    monthly_expenses = inputs['monthly_expenses']
    vacancy_months = inputs['vacancy_months']
    tax_rate = inputs['tax_rate']
    holding_period = inputs['holding_period']
    initial_fx_rate = inputs['initial_fx_rate']
    fx_appreciation = inputs['fx_appreciation']
    appreciation_rate = inputs['appreciation_rate']
    rent_growth_rate = inputs['rent_growth_rate']
    etf_return = inputs['etf_return']
    time_test_config = inputs['time_test_config']
    time_test_enabled = time_test_config['enabled']
    time_test_years = time_test_config['years']
    sale_fee_percent = inputs['sale_fee_percent']

    st.subheader("🎲 Monte Carlo Simulace")
    st.markdown("Vyhodnocení rizik pomocí simulace tisíců možných scénářů vývoje trhu.")
    
    col_mc1, col_mc2, col_mc3, col_mc4 = st.columns(4)
    with col_mc1:
        sim_count = st.number_input("Počet simulací", 100, 5000, 1000, 100)
    with col_mc2:
        vol_app = st.number_input("Volatilita cen (%)", 0.0, 10.0, 2.0, 0.1, help="Směrodatná odchylka ročního růstu ceny nemovitosti.")
    with col_mc3:
        vol_rent = st.number_input("Volatilita nájmu (%)", 0.0, 10.0, 1.5, 0.1, help="Směrodatná odchylka ročního růstu nájmu.")
    with col_mc4:
        vol_etf = 0.0
        if etf_comparison:
            vol_etf = st.number_input("Volatilita ETF (%)", 0.0, 30.0, 15.0, 1.0, help="Směrodatná odchylka ročního výnosu ETF.")
    
    if st.button("🔴 Spustit Monte Carlo Simulaci", type="primary"):
        with st.spinner(f"Probíhá výpočet {sim_count} scénářů..."):
            mc_results = calculations.run_monte_carlo(
                n_simulations=sim_count,
                # Base params
                purchase_price=purchase_price,
                down_payment=down_payment,
                one_off_costs=one_off_costs,
                interest_rate=interest_rate,
                loan_term_years=loan_term_years,
                monthly_rent=monthly_rent,
                monthly_expenses=monthly_expenses,
                vacancy_months=vacancy_months,
                tax_rate=tax_rate, 
                holding_period=holding_period,
                initial_fx_rate=initial_fx_rate,
                fx_appreciation=fx_appreciation,
                # Means
                appreciation_rate_mean=appreciation_rate,
                rent_growth_rate_mean=rent_growth_rate,
                etf_comparison=etf_comparison,
                etf_return_mean=etf_return,
                # Volatilities
                appreciation_rate_std=vol_app,
                rent_growth_rate_std=vol_rent,
                etf_return_std=vol_etf,
                time_test_enabled=time_test_enabled,
                time_test_years=time_test_years,
                sale_fee_percent=sale_fee_percent
            )
            
            # Parsing results
            df_mc = pd.DataFrame(mc_results)
            
            # --- Results Presentation ---
            st.success("Simulace dokončena!")
            
            # Metrics
            avg_irr = df_mc['irr'].mean()
            median_irr = df_mc['irr'].median()
            prob_loss = (df_mc['total_profit'] < 0).mean() * 100
            
            mc_col1, mc_col2, mc_col3 = st.columns(3)
            mc_col1.metric("Průměrné IRR", f"{avg_irr:.2f} %")
            mc_col2.metric("Medián IRR", f"{median_irr:.2f} %")
            mc_col3.metric("Pravděpodobnost ztráty", f"{prob_loss:.1f} %", delta_color="inverse")

            # Histogram IRR
            fig_hist = px.histogram(df_mc, x="irr", nbins=50, title="Rozložení dosahovaného IRR", labels={'irr': 'IRR (%)'}, color_discrete_sequence=['#4CAF50'])
            fig_hist.add_vline(x=0, line_width=3, line_dash="dash", line_color="red", annotation_text="Break-even")
            # Pokud máte proměnnou irr ze základního výpočtu, můžete ji zde použít:
            # fig_hist.add_vline(x=irr, line_width=3, line_color="blue", annotation_text="Základní scénář")
            st.plotly_chart(fig_hist, use_container_width=True)
            
            if etf_comparison:
                st.subheader("Porovnání rizik s ETF")
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Box(y=df_mc['irr'], name='Nemovitost IRR', marker_color='#4CAF50'))
                fig_comp.add_trace(go.Box(y=df_mc['etf_irr'], name='ETF IRR', marker_color='#2196F3'))
                fig_comp.update_layout(title="Rozptyl výnosů: Nemovitost vs. ETF")
                st.plotly_chart(fig_comp, use_container_width=True)
