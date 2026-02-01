
import streamlit as st
import plotly.graph_objects as go
import calculations
import numpy_financial as npf

def render_strategy_tab(inputs, metrics, derived_metrics):
    # --- 1. PŘÍPRAVA DAT (30 let horizont) ---
    STRATEGY_HORIZON_YEARS = 30
    inputs_long = inputs.copy()
    inputs_long['holding_period'] = STRATEGY_HORIZON_YEARS
    
    metrics_long = calculations.calculate_metrics(
        purchase_price=inputs_long['purchase_price'],
        down_payment=inputs_long['down_payment'],
        one_off_costs=inputs_long['one_off_costs'],
        interest_rate=inputs_long['interest_rate'],
        loan_term_years=inputs_long['loan_term_years'],
        monthly_rent=inputs_long['monthly_rent'],
        monthly_expenses=inputs_long['monthly_expenses'],
        vacancy_months=inputs_long['vacancy_months'],
        tax_rate=inputs_long['tax_rate'],
        appreciation_rate=inputs_long['appreciation_rate'],
        rent_growth_rate=inputs_long['rent_growth_rate'],
        holding_period=inputs_long['holding_period'],
        etf_comparison=inputs_long['etf_comparison'],
        etf_return=inputs_long['etf_return'],
        initial_fx_rate=inputs_long['initial_fx_rate'],
        fx_appreciation=inputs_long['fx_appreciation'],
        time_test_vars=inputs_long['time_test_config'],
        sale_fee_percent=inputs_long['sale_fee_percent']
    )

    st.header("🧭 Investiční Strategie")
    st.caption("Analýza držet vs. prodat vs. refinancovat. Efektivita kapitálu v čase.")

    # --- 2. HLAVNÍ GRAF (Kdy se to láme?) ---
    # Inputs pro strategii (Benchmark)
    with st.expander("⚙️ Nastavení Benchmarku (S čím porovnáváme?)", expanded=False):
        col_bench, _ = st.columns([1, 2])
        with col_bench:
            default_bench = inputs['etf_return'] if inputs['etf_comparison'] else 8.0
            opportunity_cost_rate = st.number_input(
                "Můj cílový výnos (% p.a.)", 
                value=default_bench, 
                step=0.5,
                help="Kolik % ročně byste vydělali jinde (např. ETF), kdybyste dům prodali?"
            )

    # Výpočet křivky ROE
    df_decision = calculations.calculate_marginal_roe(
        metrics_long, 
        purchase_price=inputs['purchase_price'],
        one_off_costs=inputs['one_off_costs'],
        sale_fee_percent=inputs['sale_fee_percent'],
        tax_rate=inputs['tax_rate'],
        time_test_vars=inputs['time_test_config'],
        etf_return_rate=opportunity_cost_rate,
        interest_rate_current=inputs['interest_rate'],
        market_refinance_rate=inputs['interest_rate'], # Default
        target_ltv_refinance=70 # Default
    )

    # Vykreslení grafu
    fig_roe = go.Figure()
    fig_roe.add_trace(go.Scatter(
        x=df_decision['Year'], y=df_decision['Marginal_ROE'],
        mode='lines', name='Výnos vašeho kapitálu v bytě (ROE)',
        line=dict(color='#2E7D32', width=4)
    ))
    fig_roe.add_trace(go.Scatter(
        x=df_decision['Year'], y=df_decision['ETF_Benchmark'],
        mode='lines', name=f'Váš cíl ({opportunity_cost_rate}%)',
        line=dict(color='#FF9800', width=2, dash='dash')
    ))
    
    # Hledání bodu zlomu
    cross_year = None
    below_target = df_decision[df_decision['Marginal_ROE'] < opportunity_cost_rate]
    if not below_target.empty:
        cross_year = int(below_target.iloc[0]['Year'])
        fig_roe.add_vline(x=cross_year, line_width=1, line_dash="dash", line_color="red")
        fig_roe.add_annotation(x=cross_year, y=opportunity_cost_rate, text=f"Bod zlomu: Rok {cross_year}", showarrow=True, arrowhead=1)

    # Vizualizace "zubu" časového testu (pokud existuje)
    time_test_vars = inputs.get('time_test_config', {})
    if time_test_vars.get('enabled', True):
        tt_years = time_test_vars.get('years', 10)
        # Spike je v roce, kdy se přechází z Taxed -> Exempt.
        # V logice: Year = tt_years (např. 10). Net_Equity(10) zdaněno, Net_Equity(11) nezdaněno.
        # Zisk za rok 11 (počítaný v řádku 10) obsahuje skok.
        if tt_years in df_decision['Year'].values:
            spike_val = df_decision.loc[df_decision['Year'] == tt_years, 'Marginal_ROE'].values[0]
            fig_roe.add_annotation(
                x=tt_years, 
                y=spike_val,
                text="Splnění časového testu (daň 0%)",
                showarrow=True,
                arrowhead=1,
                ax=0,
                ay=-40,
                font=dict(color="green")
            )

    fig_roe.update_layout(
        title="Kdy peníze 'zleniví'? (ROE vs Benchmark)",
        xaxis_title="Rok investice",
        yaxis_title="Roční výnos (%)",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_roe, use_container_width=True)

    if cross_year:
        st.info(f"💡 **Tip:** Vypadá to, že kolem **{cross_year}. roku** výnosnost klesne pod váš cíl. To je ideální čas zvážit **Prodej** nebo **Refinancování**.")
    else:
        st.success("🚀 Skvělé! Nemovitost po celých 30 let překonává váš benchmark.")

    st.markdown("---")

    # --- 3. STROJ ČASU (Ovládání) ---
    st.subheader("⏱️ Simulátor rozhodnutí")
    
    col_sim_year, col_sim_price, col_sim_rate = st.columns([1, 1, 1])
    
    with col_sim_year:
        max_year = len(df_decision)
        selected_year = st.slider("Vyberte rok rozhodnutí", 1, max_year, min(inputs['holding_period'], max_year), key="strat_year")
    
    # Get model price for selected year
    # Ensure index doesn't go out of bounds
    safe_idx = min(selected_year-1, len(metrics_long['series']['property_values'])-1)
    model_price = metrics_long['series']['property_values'][safe_idx]
    
    with col_sim_price:
        user_price_override = st.number_input(
            f"Tržní cena v r. {selected_year}", 
            value=float(model_price), step=100_000.0, format="%.0f",
            help="Za kolik byste to reálně prodali?"
        )

    with col_sim_rate:
        market_ref_rate = st.number_input(
            "Aktuální úrok hypoték (%)", 
            value=inputs['interest_rate'], step=0.1, format="%.2f",
            help="Za kolik byste si dnes půjčili?"
        )

    # --- 4. TŘI CESTY (KARTY) ---
    
    # Recalculate metrics based on overrides
    current_mtg_balance = metrics_long['series']['mortgage_balances'][safe_idx]
    
    # Helper for layout
    c_c1, c_c2, c_c3 = st.columns(3)

    # --- KARTA 1: DRŽET (HOLD) ---
    roe_now = df_decision.iloc[safe_idx]['Marginal_ROE']
    
    with c_c1:
        with st.container(border=True):
            st.markdown("### 🏠 1. Držet")
            st.caption("Nedělat nic, nechat běžet.")
            
            st.metric("Aktuální výnos (ROE)", f"{roe_now:.1f} %", delta=f"{roe_now - opportunity_cost_rate:.1f} % vs Cíl")
            
            if roe_now >= opportunity_cost_rate:
                st.success("✅ **Nechat běžet.**")
                st.caption("Peníze v domě pracují lépe než jinde.")
            else:
                st.error("⚠️ **Peníze leniví.**")
                st.caption("Vaše 'uvězněné' peníze v cihlách vydělávají méně než cíl.")

    # --- KARTA 2: PRODAT (SELL) ---
    # Need to run recalc logic to get accurate Net Liquidation Value for the overridden price
    recalc_sell = calculations.calculate_decision_metrics_for_price(
        property_value=user_price_override,
        mortgage_balance=current_mtg_balance,
        purchase_price=inputs['purchase_price'],
        one_off_costs=inputs['one_off_costs'],
        sale_fee_percent=inputs['sale_fee_percent'],
        tax_rate=inputs['tax_rate'],
        time_test_vars=inputs['time_test_config'],
        holding_years=selected_year,
        etf_return_rate=opportunity_cost_rate,
        interest_rate_current=inputs['interest_rate'],
        market_ref_rate=market_ref_rate,  
        target_ltv_ref=70
    )
    net_cash = recalc_sell['Net_Liquidation_Value']
    
    with c_c2:
         with st.container(border=True):
            st.markdown("### 💰 2. Prodat")
            st.caption("Vzít hotovost a jít jinam.")
            
            st.metric("Hotovost na ruku (Net)", f"{net_cash/1_000_000:.2f} mil.", help="Cena - Dluh - Daně - Poplatky")
            
            if roe_now < opportunity_cost_rate:
                st.success("✅ **Zvážit prodej.**")
                st.caption(f"Když {net_cash/1e6:.1f}M vložíte do ETF ({opportunity_cost_rate}%), vyděláte víc.")
            else:
                st.warning("✋ **Neprodávat.**")
                st.caption("Prodejem byste se připravili o kvalitní aktivum.")

    # --- KARTA 3: REFINANCOVAT (REFI) ---
    # Mini-control for LTV specific to Refi
    target_ltv = 70 # Default visible logic for the card view
    
    with c_c3:
        with st.container(border=True):
            st.markdown("### 🚀 3. Refinancovat")
            st.caption("Vytáhnout peníze, dům si nechat.")
            
            st.write("Cílové LTV (%)")
            target_ltv_in = st.slider("Cílové LTV", 30, 90, 70, key="refi_ltv_slider", label_visibility="collapsed")
            
            # Recalc just for this slider
            recalc_refi = calculations.calculate_decision_metrics_for_price(
                property_value=user_price_override,
                mortgage_balance=current_mtg_balance,
                purchase_price=inputs['purchase_price'],
                one_off_costs=inputs['one_off_costs'],
                sale_fee_percent=inputs['sale_fee_percent'],
                tax_rate=inputs['tax_rate'],
                time_test_vars=inputs['time_test_config'],
                holding_years=selected_year,
                etf_return_rate=opportunity_cost_rate,
                interest_rate_current=inputs['interest_rate'],
                market_ref_rate=market_ref_rate,  
                target_ltv_ref=target_ltv_in
            )
            
            cash_out = recalc_refi['Refinance_CashOut']
            benefit = recalc_refi['Refinance_Arbitrage_CZK']
            
            if cash_out <= 0:
                st.metric("Cash-Out (Do kapsy)", "0 Kč")
                st.info("🔒 **Nedostatek Equity.** Při tomto LTV nelze z nemovitosti vytáhnout žádné volné prostředky (hodnota dluhu je vyšší nebo rovna nové výši úvěru).")
            else:
                st.metric("Cash-Out (Do kapsy)", f"{cash_out/1_000_000:.2f} mil.")
                
                # Impact on payment
                new_loan = user_price_override * (target_ltv_in / 100.0)
                new_pmt = npf.pmt(market_ref_rate/1200, 30*12, -new_loan)
                
                # Need strict error handling for old payment
                try:
                    old_pmt = derived_metrics['monthly_mortgage_payment']
                except:
                    old_pmt = 0
                    
                diff_pmt = new_pmt - old_pmt
                
                if benefit > 0:
                    st.metric(
                        "Zisk navíc (Arbitráž)", 
                        f"+{int(benefit):,} Kč/rok", 
                        delta="Výhodné",
                        help="Čistý roční zisk navíc. Vznikne tak, že vytažené peníze (Cash-Out) investujete s vyšším výnosem, než je úrok hypotéky, kterou za ně platíte."
                    )
                    st.warning(f"Splátka vzroste o {int(diff_pmt):,} Kč")
                else:
                    st.metric(
                        "Zisk navíc", 
                        f"{int(benefit):,} Kč/rok", 
                        delta="Nevýhodné", 
                        delta_color="inverse",
                        help="Zde byste prodělali. Úrok hypotéky je vyšší než výnos, který byste získali investováním vytažených peněz."
                    )
                    st.markdown(f"**Negativní páka.** Úrok {market_ref_rate}% je příliš vysoký.")
