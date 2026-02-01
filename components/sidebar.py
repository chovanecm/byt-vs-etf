import streamlit as st
import calculations
import scenario_manager
import uuid
import datetime

def render_sidebar():
    st.sidebar.header("⚙️ Parametry investice")

    # Definice vizuálního layoutu (kontejnery)
    # 1. Sekce: Nákup
    c_buy = st.sidebar.container()
    # 2. Sekce: Nájem
    c_rent = st.sidebar.container()
    # 3. Sekce: Hypotéka a Strategie
    c_strat = st.sidebar.container()
    # 4. Sekce: Pokročilé (Daně, ETF)
    c_adv = st.sidebar.container()

    # --- A. POKROČILÉ NASTAVENÍ (Spouštíme nejdřív kvůli závislostem) ---
    with c_adv:
        with st.expander("⚙️ Pokročilé (Daně, ETF)", expanded=False):
            st.markdown("**Daně**")
            tax_rate = st.number_input("Daň z příjmu (%)", min_value=0.0, max_value=100.0, value=15.0, step=1.0, key="tax_rate")
            
            st.caption("Režim zdanění při prodeji:")
            tax_mode = st.radio(
                "Režim daně z prodeje", # Hidden label via label_visibility if needed, but caption is usually enough
                ["FO (Časový test)", "Vždy danit", "Nikdy nedanit"],
                index=0,
                label_visibility="collapsed",
                help="FO (Časový test) = osvobození po X letech.\nVždy danit = např. firma.\nNikdy nedanit = hrubý zisk.",
                key="tax_mode_input"
            )
            
            if tax_mode == "FO (Časový test)":
                time_test_enabled = True
                time_test_years = st.number_input("Délka časového testu (roky)", min_value=0, value=10, step=1, key="time_test_years")
            elif tax_mode == "Vždy danit":
                time_test_enabled = True
                time_test_years = 1000 # Effectively infinite
            else: # Nikdy nedanit
                time_test_enabled = False
                time_test_years = 0

            st.markdown("---")
            st.markdown("**Benchmark / Opportunity Cost**")
            etf_comparison = st.checkbox("Porovnat s ETF / Alternativou", value=True, key="etf_comparison")
            if etf_comparison:
                etf_return = st.number_input(
                    "Benchmark / Alternativní výnos (% p.a.)", 
                    min_value=0.0, value=8.0, step=0.5, key="etf_return",
                    help="Výnos, který byste získali, kdybyste peníze z prodeje nemovitosti investovali jinam (ETF, jiná nemovitost...).\nSlouží k určení bodu zvratu, kdy se vyplatí nemovitost prodat."
                )
                initial_fx_rate = st.number_input("Kurz CZK/EUR (nákup)", min_value=10.0, value=25.0, step=0.1, key="initial_fx_rate")
                fx_appreciation = st.slider("Změna kurzu (% p.a.)", -5.0, 5.0, 0.0, 0.1, help="+% = posílení EUR, -% = oslabení EUR", key="fx_appreciation")
            else:
                etf_return = 0
                initial_fx_rate = 25.0
                fx_appreciation = 0

            st.markdown("---")
            # st.markdown("**Inflace a Reálná hodnota**")
            # DRY: Use existing rent_growth_rate as general inflation proxy
            # show_real_values = st.checkbox(
            #     "Zobrazit v reálných cenách (očištěno o inflaci)", 
            #     value=False, 
            #     key="show_real_values",
            #     help="Pro přepočet na 'dnešní ceny' bude použita hodnota 'Inflace nájmu a nákladů' z sekce Nájem."
            # )
            show_real_values = False

    # --- B. PARAMETRY NÁKUPU (1. Sekce) ---
    with c_buy:
        st.subheader("1. Nákup a Růst")
        # Cena a poplatky (vstupní) - Number input (s tlačítky) pro přesné zadání
        purchase_price_m = st.number_input("Kupní cena (mil. Kč)", min_value=0.5, value=5.0, step=0.1, format="%.2f", help="Celková pořizovací cena nemovitosti.", key="purchase_price_m")
        purchase_price = purchase_price_m * 1_000_000
        
        one_off_costs = st.number_input("Vstupní poplatky (Kč)", min_value=0, value=150_000, step=10_000, help="Provize RK, právní servis, rekonstrukce před nájmem.", key="one_off_costs")
        
        # Růst ceny - Slider (včetně záporných hodnot)
        st.markdown("**Očekávání trhu**")
        appreciation_rate = st.slider("Růst ceny nemovitosti (% p.a.)", -5.0, 15.0, 3.0, 0.1, help="Roční změna tržní ceny. Záporná hodnota simuluje pokles trhu.", key="appreciation_rate")
        
        # Provize při prodeji - Number input
        sale_fee_percent = st.number_input("Náklady na budoucí prodej (% z ceny)", 0.0, 10.0, 3.0, 0.5, format="%.1f", help="Rezerva na provizi RK a právní servis při prodeji.", key="sale_fee_percent")

    # --- C. NÁJEM (2. Sekce) ---
    with c_rent:
        st.subheader("2. Nájem a Provoz")
        # Nájem a Náklady - Number inputs
        col_rent1, col_rent2 = st.columns(2)
        with col_rent1:
            monthly_rent = st.number_input("Nájemné (Kč/měs)", min_value=0, value=18000, step=500, help="Čisté nájemné bez poplatků za energie.", key="monthly_rent")
        with col_rent2:
            monthly_expenses = st.number_input("Náklady (Kč/měs)", min_value=0, value=3500, step=100, help="Fond oprav, pojištění, správa.", key="monthly_expenses")
        
        # Jednoduchý přepínač pro pokročilé nastavení nájmu
        with st.expander("⚙️ Pokročilé nastavení nájmu (Neobsazenost, Inflace)"):
             # Neobsazenost - Slider
            vacancy_months = st.slider("Neobsazenost (měsíce/rok)", 0.0, 6.0, 1.0, 0.1, help="Průměrná doba, kdy byt nebude generovat nájem.", key="vacancy_months")
            
            # Inflace - Slider
            rent_growth_rate = st.slider("Inflace nájmu a nákladů (% p.a.)", 0.0, 15.0, 2.0, 0.1, help="Očekávaný roční růst nájemného i provozních nákladů.", key="rent_growth_rate")
            
    # --- D. HYPOTÉKA A STRATEGIE (3. Sekce) ---
    with c_strat:
        st.subheader("3. Hypotéka a Strategie")
        
        # Doba a Úrok
        col_mort1, col_mort2 = st.columns(2)
        with col_mort1:
            loan_term_years = st.slider("Doba splácení (roky)", 5, 40, 30, 1, key="loan_term_years")
        with col_mort2:
            interest_rate = st.number_input("Úrok hypotéky (%)", min_value=0.0, max_value=20.0, value=5.4, step=0.1, format="%.2f", key="interest_rate")
            
        st.markdown("---")
        
        with st.expander("🤖 Optimalizátor Strategie (BETA)", expanded=False):
            st.write("**Najít nejlepší nastavení**")
            st.caption("Vyberte rozsah LTV (páky), který jste ochotni akceptovat, a nechte model najít nejvýnosnější kombinaci.")
            
            # Range slider pro optimalizaci
            opt_ltv_range = st.slider("Rozsah akceptovatelného LTV (%)", 0, 100, (20, 90), key="opt_ltv_range")
            
            if st.button("✨ Vypočítat a nastavit optimální strategii", type="primary"):
                best_irr = -999.0
                best_ltv = 0
                best_years = 0
                
                progress_bar = st.progress(0)
                # Rozsah z oboustranného slideru
                min_ltv_opt, max_ltv_opt = opt_ltv_range
                ltv_range = range(min_ltv_opt, max_ltv_opt + 1, 5)
                total_steps = len(ltv_range)
                
                for i, try_ltv in enumerate(ltv_range):
                    progress_bar.progress((i + 1) / total_steps)
                    
                    for try_year in range(1, 31):
                        try_down_payment = purchase_price * (1 - try_ltv / 100)
                        time_test_config = {"enabled": time_test_enabled, "years": time_test_years}
                        
                        res = calculations.calculate_metrics(
                            purchase_price=purchase_price,
                            down_payment=try_down_payment,
                            one_off_costs=one_off_costs,
                            interest_rate=interest_rate,
                            loan_term_years=loan_term_years,
                            monthly_rent=monthly_rent,
                            monthly_expenses=monthly_expenses,
                            vacancy_months=vacancy_months,
                            tax_rate=tax_rate, 
                            appreciation_rate=appreciation_rate,
                            rent_growth_rate=rent_growth_rate,
                            holding_period=try_year,
                            etf_comparison=False,
                            etf_return=0,
                            initial_fx_rate=25,
                            fx_appreciation=0,
                            time_test_vars=time_test_config,
                            sale_fee_percent=sale_fee_percent
                        )
                        
                        if res['irr'] > best_irr:
                            best_irr = res['irr']
                            best_ltv = try_ltv
                            best_years = try_year
                
                progress_bar.empty()
                st.session_state['opt_result'] = {
                    'ltv': best_ltv,
                    'years': best_years,
                    'irr': best_irr
                }
                
            # Zobrazení výsledku hledání
            if 'opt_result' in st.session_state:
                res = st.session_state['opt_result']
                st.info(f"💡 Nalezené optimum: LTV **{res['ltv']}%** na **{res['years']} let** (IRR {res['irr']:.2f}%)")
                
                if st.button("⬇️ Aplikovat optimum"):
                     st.session_state['target_ltv_input'] = res['ltv']
                     st.session_state['holding_period_input'] = res['years']
                     st.rerun()

        st.markdown("---")
        # Finální vstupy strategie (uživatel je může doladit po optimalizaci)
        holding_period = st.slider("Doba držení (roky)", 1, 30, step=1, key="holding_period_input")
        
        target_ltv = st.slider("LTV (%)", 0, 100, step=5, key="target_ltv_input")
        
        # Přepočet kapitálu podle LTV
        
        # 1. Spočítáme teoretickou výši hypotéky (zaokrouhleně)
        # Banky většinou neposkytují úvěry na haléře. Zaokrouhlujeme na tisíce dolů/nahoru?
        # Zde spíše dochází k floating point erroru při odečítání.
        # purchase_price (5.45 M) * (90/100) = 4.905 M
        # User claims 4.91 M shown. That is rounding.
        # User claims "úvěr byl 4 950 000".
        # 5.45 * 0.9 = 4.905. 
        # Wait, 5 450 000 * 0.9 = 4 905 000.
        # User says: "vlastní kapitál: 0.54 | Úvěr: 4.91". 
        # 0.54 + 4.91 = 5.45. This matches.
        # But user says: "myslim že tam někde dochází k zaokrouhlovacím chybám, protože ten úvěr byl 4 950 000".
        # If Loan = 4,950,000 and Price = 5,450,000.
        # LTV = 4950000 / 5450000 = 0.90825... = 90.8%.
        # So if user selects 90% LTV, loan should be 4 905 000.
        # Why does user expect 4 950 000? Maybe purchase price was 5.5M?
        # Or maybe user INPUTted loan amount directly in previous versions?
        # Current logic calculates Mortgage based on Price & LTV.
        # Ideally, we should allow precise override of Mortgage Amount OR LTV.
        
        # Let's clean up the float display first to be accurate.
        
        mortgage_amount_raw = purchase_price * (target_ltv / 100.0)
        # Zaokrouhlení na celé koruny kvůli float chybám (např. 4905000.00000001)
        mortgage_amount = round(mortgage_amount_raw)
        down_payment = purchase_price - mortgage_amount
        
        st.caption(f"Vlastní kapitál: {down_payment/1_000_000:.3f} mil. Kč | Úvěr: {mortgage_amount/1_000_000:.3f} mil. Kč")

    # Construct final inputs dictionary
    final_inputs = {
        "tax_rate": tax_rate,
        "time_test_config": {"enabled": time_test_enabled, "years": time_test_years},
        "etf_comparison": etf_comparison,
        "etf_return": etf_return,
        "initial_fx_rate": initial_fx_rate,
        "fx_appreciation": fx_appreciation,
        "general_inflation_rate": rent_growth_rate, # DRY: Using rent_growth_rate
        "show_real_values": show_real_values,
        "purchase_price": purchase_price,
        "one_off_costs": one_off_costs,
        "appreciation_rate": appreciation_rate,
        "sale_fee_percent": sale_fee_percent,
        "monthly_rent": monthly_rent,
        "monthly_expenses": monthly_expenses,
        "vacancy_months": vacancy_months,
        "rent_growth_rate": rent_growth_rate,
        "loan_term_years": loan_term_years,
        "interest_rate": interest_rate,
        "target_ltv": target_ltv,
        "holding_period": holding_period,
        "down_payment": down_payment,
        "mortgage_amount": mortgage_amount
    }

    # --- E. SPRÁVA NASTAVENÍ (Legacy JSON) ---
    with st.sidebar.expander("📂 Záloha do souboru (JSON)", expanded=False):
        # 1. Export
        st.caption("Uložit aktuální nastavení do souboru:")
        json_conf = scenario_manager.export_json()
        st.download_button(
            label="⬇️ Stáhnout JSON",
            data=json_conf,
            file_name="nastaveni_investice.json",
            mime="application/json"
        )
        
        st.markdown("---")
        
        # 2. Import
        st.caption("Načíst nastavení ze souboru:")
        
        def apply_json_import():
            if "uploaded_scenario_json" in st.session_state and st.session_state.uploaded_scenario_json:
                try:
                    string_data = st.session_state.uploaded_scenario_json.getvalue().decode("utf-8")
                    if scenario_manager.load_from_json(string_data):
                        st.session_state["import_status"] = ("success", "✅ Nastavení úspěšně načteno!")
                    else:
                        st.session_state["import_status"] = ("error", "❌ Chyba: Neplatný formát souboru.")
                except Exception as e:
                     st.session_state["import_status"] = ("error", f"❌ Chyba při načítání: {str(e)}")

        uploaded_file = st.file_uploader(
            "Vyberte soubor JSON", 
            type=["json"], 
            label_visibility="collapsed", 
            key="uploaded_scenario_json"
        )
        
        if uploaded_file is not None:
             st.button("🔄 Aplikovat JSON", on_click=apply_json_import)
             if "import_status" in st.session_state:
                 status_type, msg = st.session_state.import_status
                 if status_type == "success":
                     st.success(msg)
                 else:
                     st.error(msg)
                 del st.session_state.import_status

    return final_inputs
