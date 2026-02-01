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

    st.header("🔮 Rozhodovací Analýza (Decision Support)")
    st.markdown(f"""
    Tato sekce odpovídá na otázku: **"Mám nemovitost prodat, refinancovat, nebo držet dál v roce {holding_period}?"**
    Sleduje, jak efektivně pracují vaše peníze "uzamčené" v nemovitosti v jednotlivých letech.
    """)
    
    # --- 1. Graf ROE vs ETF ---
    st.subheader(f"Dead Equity Trap: Kdy přestává být nemovitost efektivní?")
    
    col_setup, col_chart = st.columns([1, 2])
    
    with col_setup:
        st.markdown("#### ⚙️ Parametry Simulace")
        
        # Nové parametry pro refinancování (citlivostní analýza)
        st.markdown("**Simulace Refinancování**")
        target_ltv_ref = st.slider("Cílové LTV úvěru (%)", 30, 90, 70, help="Na kolik % hodnoty nemovitosti byste si chtěli znovu půjčit?", key="target_ltv_ref")
        market_ref_rate = st.number_input("Nová úroková sazba (%)", 1.0, 10.0, 5.0, 0.1, help="Za jakou sazbu byste dnes dostali hypotéku?", key="market_ref_rate")
        
        if market_ref_rate > interest_rate:
            st.warning(f"⚠️ Pozor: Nová sazba ({market_ref_rate}%) je vyšší než současná ({interest_rate}%).")

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

    with col_chart:
        fig_roe = go.Figure()
    
    # Sloupcový graf pro Marginal ROE
    fig_roe.add_trace(go.Bar(
        x=df_decision['Year'],
        y=df_decision['Marginal_ROE'],
        name='Marginal ROE (Výnos vlastního kapitálu)',
        marker_color='#4CAF50',
        hovertemplate='Rok %{x}<br>ROE: %{y:.2f}%<extra></extra>'
    ))
    
    # Čára pro ETF Benchmark
    if etf_comparison:
        fig_roe.add_trace(go.Scatter(
            x=df_decision['Year'],
            y=df_decision['ETF_Benchmark'],
            name=f'ETF Benchmark ({etf_return}%)',
            line=dict(color='#FF5722', width=3, dash='dash'),
            hovertemplate='ETF Cíl: %{y}%<extra></extra>'
        ))
    
    fig_roe.update_layout(
        title="Meziroční výnos vs. Alternativa (ETF)",
        xaxis_title="Rok investice",
        yaxis_title="Roční výnos (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig_roe, use_container_width=True)
    
    st.caption("""
    💡 **Marginal ROE** ukazuje výnos vygenerovaný v daném roce dělený "uzamčeným" vlastním kapitálem na začátku toho roku. 
    Pokud ROE klesne pod výnos ETF, znamená to, že vaše peníze by jinde vydělávaly více (tzv. "Dead Equity Trap").
    """)

    st.divider()

    # --- 2. Analýza pro vybraný rok (Holding Period) ---
    selected_year = holding_period
    
    # Get row for selected year (Year is 1-based, index is Year-1)
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
            st.markdown("### 🚦 Doporučení")
            if gap > 0:
                st.warning(f"⚠️ **Zvažte změnu strategie!**")
                st.markdown(f"""
                V roce {selected_year} generuje vaše "umrtvená" equity ({int(equity_locked_user):,} Kč) výnos **{roe_now:.2f} %**, 
                což je **MÉNĚ** než alternativní ETF ({etf_now} %).
                
                **Možnosti:**
                1. **Refinancovat:** Vytáhněte hotovost a investujte ji.
                2. **Prodat:** Přesuňte kapitál do efektivnějšího aktiva.
                """)
            else:
                st.success(f"✅ **Držet**")
                st.markdown(f"""
                Nemovitost stále vydělává **efektivněji ({roe_now:.2f} %)** než alternativa. 
                Pákový efekt stále funguje ve váš prospěch.
                """)

        with c_dec2:
            st.markdown("### 🏦 Refinancování (Equity Release)")
            
            # rate_spread unused
            
            if refinance_amount > 100000:
                # 1. Částka k dispozici
                st.metric(
                    label=f"Možný Cash-Out (při {target_ltv_ref}% LTV)", 
                    value=f"{int(refinance_amount):,} Kč",
                    delta="Likvidita k uvolnění",
                    delta_color="normal"
                )
                
                # 2. Arbitrážní analýza
                st.markdown("#### ⚖️ Analýza výhodnosti")
                # Vysvětlení spreadu už není jednoduché číslo, spíše výsledek v CZK
                
                if refinance_benefit > 0:
                    st.success(f"✅ **Doporučeno:** Arbitráž je zisková.")
                    st.metric(
                        label="Očekávaný čistý zisk z refinancování",
                        value=f"+{int(refinance_benefit):,} Kč / rok",
                        delta="Arbitrážní zisk",
                        delta_color="normal"
                    )
                    st.info(f"I když zaplatíte vyšší úroky ({market_ref_rate}%) z celého dluhu, výnos z uvolněné hotovosti to překoná.")
                else:
                    st.error(f"⛔ **Nevýhodné:** Náklady převyšují výnosy.")
                    st.metric(
                        label="Očekávaná ztráta z operace",
                        value=f"{int(refinance_benefit):,} Kč / rok",
                        delta="Negativní dopad",
                        delta_color="inverse"
                    )
                    st.markdown(f"Při nové sazbě **{market_ref_rate} %** se refinancování celého dluhu nevyplatí, protože vyšší splátky 'sežerou' výnos z investice.")
            else:
                st.metric(
                    label="Možný Cash-Out (při 70% LTV)", 
                    value="0 Kč",
                )
                st.markdown("Zatím není dostatek volné equity pro smysluplné refinancování.")

    st.divider()
    
    # --- 3. Projekce Sell vs. Hold ---
    st.subheader(f"🔮 Projekce na dalších 10 let: Prodat vs. Držet")
    st.markdown("Co se stane s vaším majetkem v příštích 10 letech, pokud se rozhodnete právě teď?")
    
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
