import streamlit as st
import plotly.graph_objects as go
import calculations

def render_strategy_tab(inputs, metrics, derived_metrics):
    # Unpack
    holding_period = inputs['holding_period']
    purchase_price = inputs['purchase_price']
    one_off_costs = inputs['one_off_costs']
    sale_fee_percent = inputs['sale_fee_percent']
    tax_rate = inputs['tax_rate']
    time_test_config = inputs['time_test_config']
    etf_comparison = inputs['etf_comparison']
    etf_return = inputs['etf_return']
    interest_rate = inputs['interest_rate']
    appreciation_rate = inputs['appreciation_rate']
    
    monthly_mortgage_payment = derived_metrics['monthly_mortgage_payment']

    st.header("🔮 Strategický Kompas")
    st.markdown("Nástroj pro řízení životního cyklu investice. Pomáhá určit, kdy je čas **držet**, **refinancovat**, nebo **prodat**.")
    
    # --- 1. SETTINGS & CHART (Context) ---
    
    # Expander pro nastavení, aby nerušil graf
    with st.expander("⚙️ Nastavení simulace trhu (Refinancování & Benchmark)", expanded=False):
        c_set1, c_set2 = st.columns(2)
        with c_set1:
            st.markdown("**Benchmark (Alternativa)**")
            st.caption(f"Porovnáváme s výnosem: **{etf_return if etf_comparison else 0} % p.a.**")
            if not etf_comparison:
                st.warning("⚠️ Nemáte zapnuté porovnání s ETF v levém menu.")
        
        with c_set2:
            st.markdown("**Refinancování (Tržní podmínky)**")
            target_ltv_ref = st.slider("Cílové LTV nové hypotéky (%)", 30, 90, 70, key="target_ltv_ref")
            market_ref_rate = st.number_input("Aktuální sazba hypoték (%)", 1.0, 10.0, inputs['interest_rate'], 0.1, key="market_ref_rate")

    # Výpočet decision metrik s novými inputy
    df_decision = calculations.calculate_marginal_roe(
        metrics, 
        purchase_price=purchase_price,
        one_off_costs=one_off_costs,
        sale_fee_percent=sale_fee_percent,
        tax_rate=tax_rate,
        time_test_vars=time_test_config,
        etf_return_rate=etf_return if etf_comparison else 0,
        interest_rate_current=interest_rate,
        market_refinance_rate=market_ref_rate,
        target_ltv_refinance=target_ltv_ref
    )

    # FULL WIDTH CHART
    st.subheader("1. Mapa efektivity kapitálu")
    st.caption("Kdy začne být vaše investice 'líná'? Sledujte, kde se zelená křivka (Nemovitost) protne s oranžovou (Benchmark).")

    fig_roe = go.Figure()
    
    # ROE Line
    fig_roe.add_trace(go.Scatter(
        x=df_decision['Year'],
        y=df_decision['Marginal_ROE'],
        mode='lines+markers',
        name='Výnos Equity (ROE) Nemovitosti',
        line=dict(color='#2E7D32', width=4), # Tmavší zelená
        marker=dict(size=8, color='#2E7D32'),
        hovertemplate='Rok %{x}<br>Výnos Equity: %{y:.2f}%<extra></extra>'
    ))
    
    # Benchmark Line
    if etf_comparison:
        fig_roe.add_trace(go.Scatter(
            x=df_decision['Year'],
            y=df_decision['ETF_Benchmark'],
            mode='lines',
            name=f'Váš Cíl / Benchmark ({etf_return}%)',
            line=dict(color='#FF5722', width=3, dash='dash'),
            hovertemplate='Benchmark: %{y}%<extra></extra>'
        ))
    
    fig_roe.update_layout(
        xaxis_title="Rok od nákupu",
        yaxis_title="Roční efektivita (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        height=320
    )
    
    st.plotly_chart(fig_roe, use_container_width=True)

    # Interpretace - Alert
    below_target = df_decision[df_decision['Marginal_ROE'] < df_decision['ETF_Benchmark']]
    if not below_target.empty:
        cross_year = int(below_target.iloc[0]['Year'])
        st.warning(f"📉 **Varování:** Od **roku {cross_year}** klesá efektiva nemovitosti pod váš cíl. Peníze začínají 'lenivět'.")
    else:
        st.success(f"🚀 **Skvělé:** Po celou dobu {len(df_decision)} let nemovitost překonává váš benchmark. Kapitál pracuje efektivně.")

    st.markdown("---")

    # --- 2. TIME MACHINE & DIAGNOSTICS ---
    st.subheader(f"2. Diagnostika v čase")
    
    # Slider jako hlavní ovládací prvek
    col_slide, _ = st.columns([2,1])
    with col_slide:
        selected_year = st.slider(
            "⏱️ Vyberte rok, ve kterém se rozhodujete:", 
            min_value=1, 
            max_value=len(df_decision), 
            value=holding_period,
            key="strategy_year_selector_main"
        )
    
    # Get row for selected year
    if selected_year <= len(df_decision):
        row = df_decision.iloc[selected_year - 1]
        
        # --- INPUT: Override pro aktuální cenu ---
        st.subheader(f"Detailní Rozhodování pro Rok {selected_year}")
        
        # Default value from model
        model_price = metrics['series']['property_values'][selected_year-1]
        
        # UX Fix: Pokud uživatel změní rok (holding_period), chceme aktualizovat předvyplněnou cenu (override).
        # Princip nejmenšího překvapení: Uživatel očekává, že override se týká vybraného roku.
        # Check if year changed since last render
        if "last_selected_year" not in st.session_state:
            st.session_state["last_selected_year"] = selected_year
        
        if st.session_state["last_selected_year"] != selected_year:
             # Reset override to model price for the new year
             st.session_state["price_override"] = float(model_price)
             st.session_state["last_selected_year"] = selected_year

        col_price_override, _ = st.columns([1, 2])
        with col_price_override:
             user_price_override = st.number_input(
                 f"Aktuální tržní cena v roce {selected_year} (Kč)", 
                 value=float(model_price), 
                 step=100_000.0, 
                 format="%.0f",
                 help="Můžete upravit odhad ceny pro přesnější výpočet možností refinancování a prodeje.",
                 key="price_override"
             )
        
        # Pře-počítání metrik pro tento konkrétní vstup
        # Použijeme dluh z modelu (ten je daný splátkovým kalendářem), ale cenu od uživatele
        current_mtg_balance = metrics['series']['mortgage_balances'][selected_year-1]
        
        override_metrics = calculations.calculate_decision_metrics_for_price(
            property_value=user_price_override,
            mortgage_balance=current_mtg_balance,
            purchase_price=purchase_price,
            one_off_costs=one_off_costs,
            sale_fee_percent=sale_fee_percent,
            tax_rate=tax_rate,
            time_test_vars=time_test_config,
            holding_years=selected_year,
            target_ltv_ref=target_ltv_ref,
            market_ref_rate=market_ref_rate,
            interest_rate_current=interest_rate,
            etf_return_rate=etf_return if etf_comparison else 0
        )
        
        # Update values for display
        roe_now = row['Marginal_ROE'] # ROE necháme z modelu (historické) nebo bychom museli přepočítat i Equity_Start. Pro jednoduchost bereme model.
        etf_now = row['ETF_Benchmark']
        gap = row['Gap']
        
        # Těmito hodnotami nahradíme ty z tabulky pro sekci níže
        refinance_amount = override_metrics['Refinance_CashOut']
        refinance_benefit = override_metrics['Refinance_Arbitrage_CZK']
        net_liquidation_value_user = override_metrics['Net_Liquidation_Value']
        
        equity_locked_user = user_price_override - current_mtg_balance # Simple equity at end of year
        
        # --- DEBUG INFO ---
        # st.caption(f"🔧 DIAGNOSTIKA: Cena={user_price_override/1e6:.2f}M, Dluh={current_mtg_balance/1e6:.2f}M, Equity(Hold)={equity_locked_user/1e6:.2f}M, Cash(Sell)={net_liquidation_value_user/1e6:.2f}M")
        
        c_dec1, c_dec2 = st.columns([1, 1])
        
        with c_dec1:
            st.markdown("### 1. Diagnostika: Líný nebo pilný kapitál?")
            st.caption("Porovnáváme výnos vaší 'uvězněné' equity v nemovitosti oproti vašemu benchmarku.")
            
            if gap > 0:
                st.warning(f"⚠️ **Kapitál leniví (ROE < Benchmark)**")
                st.markdown(f"""
                Váš milion korum v nemovitosti ("Net Equity") nyní vydělává jen **{roe_now:.2f} % ročně**. 
                Kdybyste nemovitost prodali a peníze dali do vašeho benchmarku ({etf_now} %), **vyděláte více**.
                
                **Možnosti:**
                1. **Prodat:** Ukončit investici a přesunout kapitál.
                2. **Agresivně refinancovat:** Snížit equity v domě (viz vpravo) a zvýšit celkové ROE.
                """)
            else:
                st.success(f"✅ **Kapitál pracuje tvrdě (ROE > Benchmark)**")
                st.markdown(f"""
                Výnos vaší equity v nemovitosti (**{roe_now:.2f} %**) stále překonává vaši alternativu ({etf_now} %).
                
                Z pohledu efektivity kapitálu **dává smysl nemovitost dále držet**.
                """)

        with c_dec2:
            st.markdown("### 2. Turbo efekt: Refinancování")
            st.caption("Můžeme zvýšit výnos tím, že si půjčíme levné peníze proti domu a zainvestujeme je?")
            
            # rate_spread unused
            
            if refinance_amount > 100000:
                # 1. Částka k dispozici
                st.metric(
                    label=f"Hodnota pro další nákup (Cash-Out)", 
                    value=f"{int(refinance_amount):,} Kč",
                    delta="Možná akontace na další byt",
                    delta_color="normal"
                )
                
                # 2. Arbitrážní analýza
                # Vysvětlení spreadu už není jednoduché číslo, spíše výsledek v CZK
                
                if refinance_benefit > 0:
                    st.success(f"✅ **Doporučeno: Pozitivní páka**")
                    st.markdown(f"**Co to znamená?**")
                    st.markdown(f"Vyplatí se vzít si hypotéku (i s úrokem {market_ref_rate}%) a vytažené peníze investovat do benchmarku.")
                    st.metric(
                        label="Čistý zisk navíc (Arbitráž)",
                        value=f"+{int(refinance_benefit):,} Kč / rok",
                        help="O tolik bohatší budete každý rok, pokud provedete refinancování a investici, oproti stavu, kdy jen 'držíte'."
                    )
                else:
                    st.error(f"⛔ **Nevýhodné: Negativní páka**")
                    st.markdown("Úrok nové hypotéky je moc vysoký. Vytažené peníze by v benchmarku nevydělaly ani na splátky úroků.")
            else:
                st.info("Zatím nemáte v domě dostatek volného kapitálu (Equity) pro smysluplné refinancování.")

    st.divider()
    
    # --- 3. Projekce Sell vs. Hold ---
    st.subheader(f"🔮 Projekce budoucnosti (10 let)")
    st.markdown("Jaký dopad na váš celkový majetek bude mít, když se **DNES** rozhodnete prodat, nebo držet?")
    st.caption("Rozdíl oproti grafu Opportunity Cost: Tam vidíte roční procenta. Zde vidíte kumulované miliony na účtu.")
    
    # Prepare inputs for projection
    # Need current values from 'row' (based on Selected Year)
    # But 'row' variable from above is a Series.
    # We need inputs for calculations.project_future_wealth
    # Current values come from the Series:
    
    # Property Value at selected year (OVERRIDDEN)
    val_now = user_price_override
    # Mortgage Balance at selected year (MODEL)
    mtg_now = current_mtg_balance
    # Net Liquidation Value (OVERRIDDEN)
    cash_now = net_liquidation_value_user
    
    if cash_now > 0:
        df_proj = calculations.project_future_wealth(
            start_property_value=val_now,
            start_mortgage_balance=mtg_now,
            net_liquidation_value=cash_now,
            monthly_payment=monthly_mortgage_payment,
            mortgage_rate=interest_rate,
            appreciation_rate=appreciation_rate,
            etf_return_rate=etf_return if etf_comparison else 0,
            projection_years=10
        )
        
        # Plot
        fig_proj = go.Figure()
        
        # HOLD Trace
        fig_proj.add_trace(go.Scatter(
            x=df_proj['Year_Relative'] + selected_year,
            y=df_proj['NW_Hold'],
            mode='lines+markers',
            name='Strategie: DRŽET (Net Worth)',
            line=dict(color='#4CAF50', width=3)
        ))
        
        # SELL Trace
        fig_proj.add_trace(go.Scatter(
            x=df_proj['Year_Relative'] + selected_year,
            y=df_proj['NW_Sell'],
            mode='lines+markers',
            name='Strategie: PRODAT a ETF (Net Worth)',
            line=dict(color='#2196F3', width=3, dash='dot')
        ))
        
        fig_proj.update_layout(
            title=f"Vývoj čistého bohatství (Net Worth) - Start: Rok {selected_year}",
            xaxis_title="Rok v budoucnu",
            yaxis_title="Net Worth (Kč)",
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_proj, use_container_width=True)
        
        # Conclusion Text
        final_hold = df_proj['NW_Hold'].iloc[-1]
        final_sell = df_proj['NW_Sell'].iloc[-1]
        diff = final_sell - final_hold
        
        st.markdown("#### 🏁 Závěr projekce")
        if diff > 0:
            st.info(f"💡 Pokud byste nyní prodali a investovali do ETF, za 10 let byste mohli mít o **{int(diff):,} Kč více** než při držení nemovitosti.")
        else:
            st.success(f"💡 Pokud si nemovitost ponecháte, za 10 let budete mít o **{int(abs(diff)):,} Kč více** než kdybyste ji nyní prodali.")
            
    else:
        st.warning("V tomto roce by prodej generoval ztrátu nebo nulový kapitál, projekce 'Prodat' není relevantní.")

    st.markdown("---")
