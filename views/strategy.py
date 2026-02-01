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
    
    # --- 1. SETTINGS (Split for clarity) ---
    
    st.info("💡 **Jak číst tento graf:** Zelená křivka ukazuje, jak tvrdě pracují vaše peníze v nemovitosti (ROE). Jakmile klesne pod vaši alternativu (oranžová čára), vaše peníze 'zlenivěly' a je čas zvážit prodej nebo refinancování.")

    col_inputs_1, col_inputs_2 = st.columns([1, 1])
    
    with col_inputs_1:
         # MAIN DECISION INPUT
        st.markdown("### 🎯 S čím porovnáváme?")
        default_benchmark = etf_return if etf_comparison else 8.0
        
        opportunity_cost_rate = st.number_input(
            "Alternativní výnos (Opportunity Cost) % p.a.", 
            min_value=0.0, 
            max_value=30.0, 
            value=default_benchmark, 
            step=0.5,
            help="Pokud nemovitost prodáte a peníze investujete jinam (např. ETF nebo jiný byt), kolik očekáváte výnos? Toto je vaše 'laťka', kterou musí nemovitost překonat.",
            key="strat_opp_cost_rate"
        )
    
    # Placeholder for layout balance if needed
    with col_inputs_2:
        st.write("") # Empty 

    # --- SIMULACE DLOUHÉHO HORIZONTU (30 let) ---
    # Aby uživatel viděl křivku i ZA hranicí svého původního holding_period
    STRATEGY_HORIZON_YEARS = 30
    
    # Vytvoříme kopii vstupů a přepíšeme holding_period pro účely strategie
    inputs_long = inputs.copy()
    inputs_long['holding_period'] = STRATEGY_HORIZON_YEARS
    
    # Přepočítáme metriky pro dlouhý horizont
    # Musíme explicitně namapovat argumenty, protože inputs dict používá jiné klíče než funkce (např. time_test_config vs time_test_vars)
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
        time_test_vars=inputs_long['time_test_config'], # ZDE BYL PROBLÉM (mapping config -> vars)
        sale_fee_percent=inputs_long['sale_fee_percent']
    )

    # Výpočet decision metrik s lokálním opportunity cost na dlouhém horizontu
    df_decision = calculations.calculate_marginal_roe(
        metrics_long, 
        purchase_price=purchase_price,
        one_off_costs=one_off_costs,
        sale_fee_percent=sale_fee_percent,
        tax_rate=tax_rate,
        time_test_vars=time_test_config,
        etf_return_rate=opportunity_cost_rate, # POUŽIJEME LOKÁLNÍ INPUT
        interest_rate_current=interest_rate,
        market_refinance_rate=interest_rate, # Default pro graf (nepouziva se)
        target_ltv_refinance=70 # Default pro graf (nepouziva se)
    )

    # FULL WIDTH CHART
    st.subheader("1. Mapa efektivity kapitálu")
    st.caption(f"Srovnáváme výnos vaší Equity (zelená) vs. Nová příležitost {opportunity_cost_rate}% (oranžová).")

    fig_roe = go.Figure()
    
    # ROE Line
    fig_roe.add_trace(go.Scatter(
        x=df_decision['Year'],
        y=df_decision['Marginal_ROE'],
        mode='lines', # Odstraněny markers pro čistší look na dlouhé křivce
        name='Výnos Equity (ROE) Nemovitosti',
        line=dict(color='#2E7D32', width=4), # Tmavší zelená
        marker=dict(size=8, color='#2E7D32'),
        hovertemplate='Rok %{x}<br>Výnos Equity: %{y:.2f}%<extra></extra>'
    ))
    
    # Benchmark Line (Active Opportunity)
    fig_roe.add_trace(go.Scatter(
        x=df_decision['Year'],
        y=df_decision['ETF_Benchmark'],
        mode='lines',
        name=f'Nová příležitost ({opportunity_cost_rate}%)',
        line=dict(color='#FF9800', width=3, dash='dashdot'), # Oranžová pro "Switch"
        hovertemplate='Cíl: %{y}%<extra></extra>'
    ))
    
    # Původní Global Benchmark (Passive) - volitelně pro kontext?
    # Nechme to jednoduché. Uživatel si opportunity cost definoval nahoře.
    
    fig_roe.update_layout(
        xaxis_title="Rok od nákupu",
        yaxis_title="Roční efektivita (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        height=320
    )
    
    # Přidat vertikální čáru pro aktuálně zvolený Holding Period
    fig_roe.add_vline(
        x=holding_period, 
        line_width=2, 
        line_dash="dot", 
        line_color="gray", 
        annotation_text="Váš plán (zleva)", 
        annotation_position="top right"
    )
    
    st.plotly_chart(fig_roe, use_container_width=True)

    # Interpretace - Alert
    below_target = df_decision[df_decision['Marginal_ROE'] < df_decision['ETF_Benchmark']]
    if not below_target.empty:
        cross_year = int(below_target.iloc[0]['Year'])
        st.warning(f"📉 **Bod zlomu (Rok {cross_year}):** Od tohoto roku by se vyplatilo prodat a peníze přesunout do vaší nové příležitosti ({opportunity_cost_rate}%).")
    else:
        st.success(f"🚀 **Skvělé:** Po celou dobu {len(df_decision)} let nemovitost překonává vaši alternativu ({opportunity_cost_rate}%). Není důvod prodávat.")

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
            value=holding_period if holding_period <= len(df_decision) else 10,
            key="strategy_year_selector_main"
        )
    
    # Get row for selected year (row is Series from LONG metrics)
    if selected_year <= len(df_decision):
        row = df_decision.iloc[selected_year - 1]

        
        # --- INPUT: Override pro aktuální cenu ---
        st.subheader(f"Detailní Rozhodování pro Rok {selected_year}")
        
        # Default value from model (Using metrics_long to support years beyond holding_period)
        model_price = metrics_long['series']['property_values'][selected_year-1]
        
        # UX Fix: Pokud uživatel změní rok (holding_period), chceme aktualizovat předvyplněnou cenu (override).
        # Princip nejmenšího překvapení: Uživatel očekává, že override se týká vybraného roku.
        # Check if year changed since last render
        if "last_selected_year" not in st.session_state:
            st.session_state["last_selected_year"] = selected_year
        
        if st.session_state["last_selected_year"] != selected_year:
             # Reset override to model price for the new year
             st.session_state["price_override"] = float(model_price)
             st.session_state["last_selected_year"] = selected_year

        # Zobrazení detailního rozhodování
        
        # Levý sloupec: Override ceny
        col_price_adjust, col_refinance_control = st.columns([1, 1])

        with col_price_adjust:
             st.subheader(f"Detailní Rozhodování pro Rok {selected_year}")
             st.caption("Pohled pod kapotu: Změňte parametry a sledujte dopad.")
             user_price_override = st.number_input(
                 f"Aktuální tržní cena v roce {selected_year} (Kč)", 
                 value=float(model_price), 
                 step=100_000.0, 
                 format="%.0f",
                 help="Můžete upravit odhad ceny pro přesnější výpočet možností refinancování a prodeje.",
                 key="price_override"
             )

        # Pravý sloupec: Kontrola refinancování
        with col_refinance_control:
             st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True) # Spacer
             with st.container(border=True): # Oranžový rámeček nebo border
                 st.caption("🔧 Parametry pro Turbo Efekt")
                 cr1, cr2 = st.columns(2)
                 with cr1:
                     target_ltv_ref = st.slider("Cílové LTV (%)", 30, 90, 70, key="target_ltv_ref_detail")
                 with cr2:
                     market_ref_rate = st.number_input("Očk. Úrok (%)", 1.0, 10.0, inputs['interest_rate'], 0.1, key="market_ref_rate_detail")

        # Pře-počítání metrik pro tento konkrétní vstup
        # Použijeme dluh z modelu (ten je daný splátkovým kalendářem), ale cenu od uživatele
        current_mtg_balance = metrics_long['series']['mortgage_balances'][selected_year-1]
        
        override_metrics = calculations.calculate_decision_metrics_for_price(
            property_value=user_price_override,
            mortgage_balance=current_mtg_balance,
            purchase_price=purchase_price,
            one_off_costs=one_off_costs,
            sale_fee_percent=sale_fee_percent,
            tax_rate=tax_rate,
            time_test_vars=time_test_config,
            holding_years=selected_year,
            etf_return_rate=opportunity_cost_rate,
            interest_rate_current=interest_rate,
            market_ref_rate=market_ref_rate,
            target_ltv_ref=target_ltv_ref
        )
        
        # Update values for display
        roe_now = row['Marginal_ROE'] 
        etf_now = row['ETF_Benchmark']
        gap = row['Gap']
        
        refinance_amount = override_metrics['Refinance_CashOut']
        refinance_benefit = override_metrics['Refinance_Arbitrage_CZK']
        net_liquidation_value_user = override_metrics['Net_Liquidation_Value']
        
        # --- ROZDĚLENÍ DLOUHÉ SEKCE (Diagnostika / Turbo) ---
        st.divider()
        
        c_diag, c_turbo = st.columns([1, 1])
        
        # --- 1. DIAGNOSTIKA (Vlevo) ---
        with c_diag:
            st.markdown("### 1. Diagnostika: Líný nebo pilný kapitál?")
            st.caption("Porovnáváme výnos vaší 'uvězněné' equity v nemovitosti oproti vašemu benchmarku.")
            
            # Gauge chart / Metric logic
            if gap > 0:
                st.warning(f"⚠️ **Kapitál leniví (ROE < Benchmark)**")
                st.markdown(f"""
                Váš milion korum v nemovitosti ("Net Equity") nyní vydělává jen **{roe_now:.2f} % ročně**. 
                Kdybyste nemovitost prodali a peníze dali do vašeho benchmarku ({etf_now} %), **vyděláte více**.
                """)
                st.info("💡 **Doporučení:** Zvažte prodej nebo agresivní refinancování (viz vpravo).")
            else:
                st.success(f"✅ **Kapitál pracuje tvrdě (ROE > Benchmark)**")
                st.markdown(f"""
                Výnos vaší equity v nemovitosti (**{roe_now:.2f} %**) stále překonává vaši alternativu ({etf_now} %).
                """)
                st.caption("Z pohledu efektivity kapitálu dává smysl nemovitost dále držet.")

        # --- 2. TURBO EFEKT (Vpravo) ---
        with c_turbo:
            st.markdown("### 2. Turbo efekt: Refinancování")
            st.caption(f"Simulace vytažení hotovosti při **{target_ltv_ref}% LTV** a úroku **{market_ref_rate}%**.")
            
            if refinance_amount > 100000:
                tur_c1, tur_c2 = st.columns(2)
                with tur_c1:
                   st.metric(
                    label="Cash-Out (Hotovost)", 
                    value=f"{int(refinance_amount/1000):,} tis. Kč",
                    help="Čistá hotovost, kterou získáte po refinancování a splacení původního úvěru."
                   )
                with tur_c2:
                    color_arb = "normal" if refinance_benefit > 0 else "inverse"
                    st.metric(
                        label="Arbitráž (Zisk/rok)",
                        value=f"{int(refinance_benefit):,} Kč",
                        delta="Výhodné" if refinance_benefit > 0 else "Nevýhodné",
                        delta_color=color_arb,
                        help="Rozdíl mezi výnosem investovaného Cash-Outu a zvýšenou splátkou úroků."
                    )

                if refinance_benefit > 0:
                    st.success(f"✅ **Pozitivní páka:** Vyplatí se.")
                else:
                    st.error(f"⛔ **Negativní páka:** Nový úrok je moc drahý.")
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
