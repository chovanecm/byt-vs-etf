import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go
import calculations  # Import externích výpočtů

# Nastavení stránky
st.set_page_config(page_title="Investiční kalkulačka", layout="wide", initial_sidebar_state="expanded")

# Inicializace session state
if "target_ltv_input" not in st.session_state:
    st.session_state["target_ltv_input"] = 80
if "holding_period_input" not in st.session_state:
    st.session_state["holding_period_input"] = 10
if "input_type_mode" not in st.session_state:
    st.session_state["input_type_mode"] = "LTV (%)"

st.title("🏢 Analýza Investičního Bytu")
st.markdown("Interaktivní nástroj pro modelování výnosnosti investice do nemovitosti.")

# --- Sidebar Vstupy ---
st.sidebar.header("⚙️ Parametry investice")

# Sekce 1: Nákup a Hypotéka
with st.sidebar.expander("💰 Nákup a financování", expanded=True):
    # Cena nemovitosti
    purchase_price_m = st.number_input("Kupní cena bytu (v mil. Kč)", min_value=1.0, value=5.0, step=0.1)
    purchase_price = purchase_price_m * 1_000_000

    # Vlastní kapitál
    input_type = st.radio("Zadat vlastní kapitál:", ["LTV (%)", "Částka (mil. Kč)"], horizontal=True, key="input_type_mode")
    
    if input_type == "LTV (%)":
        target_ltv = st.slider("Požadované LTV (%)", 0, 100, step=5, help="Loan-to-Value: Kolik % ceny tvoří hypotéka.", key="target_ltv_input")
        down_payment = purchase_price * (1 - target_ltv / 100)
        st.write(f"💵 Vlastní zdroje: **{down_payment / 1_000_000:.2f} mil. Kč**")
    else:
        down_payment_m = st.number_input("Vlastní kapitál (v mil. Kč)", min_value=0.0, max_value=purchase_price_m, value=1.0, step=0.1)
        down_payment = down_payment_m * 1_000_000
        current_ltv = 100 * (1 - down_payment / purchase_price) if purchase_price > 0 else 0
        st.write(f"📊 Odpovídá LTV: **{current_ltv:.1f} %**")

    # Jednorázové náklady
    one_off_costs = st.number_input("Jednorázové náklady (Kč)", min_value=0, value=150_000, step=10_000, help="Provize RK, právní servis, daně, renovace.")

    mortgage_amount = purchase_price - down_payment
    if mortgage_amount < 0:
        mortgage_amount = 0

    st.markdown("---")
    st.markdown("**Hypotéka**")
    interest_rate = st.number_input("Úroková sazba (%)", min_value=0.0, value=5.4, step=0.1)
    loan_term_years = st.number_input("Doba splácení (roky)", min_value=1, max_value=40, value=30, step=1)

# Sekce 2: Cashflow
with st.sidebar.expander("🏠 Nájem a provoz", expanded=True):
    monthly_rent = st.number_input("Měsíční nájemné (Kč)", min_value=0, value=18_000, step=500)
    monthly_expenses = st.number_input("Měsíční náklady (Kč)", min_value=0, value=3_500, step=100, help="Fond oprav, pojištění, správa, daň z nemovitosti")
    vacancy_months = st.slider("Neobsazenost (měsíce/rok)", 0.0, 3.0, 1.0, 0.1, help="Průměrný počet měsíců v roce, kdy byt nevydělává.")

# Sekce 2b: Daně a Poplatky
with st.sidebar.expander("💸 Daně a Poplatky", expanded=False):
    tax_rate = st.number_input("Daň z příjmu (%)", min_value=0.0, max_value=100.0, value=15.0, step=1.0, help="Sazba daně z příjmu (nájem i zisk z prodeje).", key="tax_rate")
    
    sale_fee_percent = st.number_input("Poplatek při prodeji (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.5, help="Např. provize realitní kanceláři (z prodejní ceny).", key="sale_fee_percent")

    st.markdown("---")
    time_test_enabled = st.checkbox("Zohlednit časový test", value=True, help="Osvobození od daně ze zisku při prodeji po určité době.", key="time_test_enabled")
    if time_test_enabled:
        time_test_years = st.number_input("Délka časového testu (roky)", min_value=0, value=10, step=1, key="time_test_years")
    else:
        time_test_years = 10 # Default fall

# Sekce 3: Projekce (Trh)
with st.sidebar.expander("📈 Tržní predikce", expanded=False):
    appreciation_rate = st.slider("Růst ceny nemovitosti (% p.a.)", 0.0, 10.0, 3.0, 0.1)
    rent_growth_rate = st.slider("Inflace nájmu a nákladů (% p.a.)", 0.0, 10.0, 2.0, 0.1)

# Sekce 4: Strategie
st.sidebar.subheader("Strategie")
holding_period = st.sidebar.slider("Doba držení (roky)", 1, 30, step=1, key="holding_period_input")

# Sekce 5: Alternativní investice
with st.sidebar.expander("📊 Alternativa (ETF)", expanded=False):
    etf_comparison = st.checkbox("Porovnat s ETF", value=True)
    if etf_comparison:
        etf_return = st.number_input("Očekávaný výnos ETF (% p.a.)", min_value=0.0, value=8.0, step=0.5)
        
        st.markdown("**Kurzové riziko (CZK/EUR)**")
        initial_fx_rate = st.number_input("Kurz CZK/EUR (nákup)", min_value=10.0, value=25.0, step=0.1)
        fx_appreciation = st.slider("Změna kurzu (% p.a.)", -5.0, 5.0, 0.0, 0.1, 
                                           help="+% = posílení EUR (zisk), -% = oslabení EUR")
    else:
        etf_return = 0
        initial_fx_rate = 25.0
        fx_appreciation = 0

# Sekce 6: Optimalizace
st.sidebar.markdown("---")
with st.sidebar.expander("✨ Optimalizace Strategie", expanded=False):
    st.markdown("Najdi nejlepší kombinaci LTV a Doby držení pro max. IRR.")
    opt_min_ltv = st.number_input("Min. LTV (%)", 0, 100, 20, 5)
    opt_max_ltv = st.number_input("Max. LTV (%)", 0, 100, 90, 5)
    
    if st.button("🔍 Najít optimální strategii"):
        best_irr = -999.0
        best_ltv = 0
        best_years = 0
        
        progress_bar = st.progress(0)
        ltv_range = range(int(opt_min_ltv), int(opt_max_ltv) + 1, 5)
        total_steps = len(ltv_range)
        
        for i, try_ltv in enumerate(ltv_range):
            progress_bar.progress((i + 1) / total_steps)
            
            for try_year in range(1, 31):
                try_down_payment = purchase_price * (1 - try_ltv / 100)
                
                # Předpoklad: Standardní daň 15% (není v UI)
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
                    time_test_vars=time_test_config
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
    
    if 'opt_result' in st.session_state:
        res = st.session_state['opt_result']
        st.success(f"**Nalezeno:**\n\nLTV: {res['ltv']} %\n\nDoba: {res['years']} let\n\nIRR: {res['irr']:.2f} %")
        
        def apply_strategy(ltv, years):
            st.session_state['input_type_mode'] = "LTV (%)"
            st.session_state['target_ltv_input'] = ltv
            st.session_state['holding_period_input'] = years
            
        st.button("🚀 Použít tuto strategii", on_click=apply_strategy, args=(res['ltv'], res['years']))


# --- Výpočty ---
# (Všechna logika je nyní v modulu calculations.py pro zachování Orthogonality)

try:
    # Konfigurace pro časový test
    time_test_config = {"enabled": time_test_enabled, "years": time_test_years}

    # Volání centrální výpočetní funkce
    metrics = calculations.calculate_metrics(
        purchase_price=purchase_price,
        down_payment=down_payment,
        one_off_costs=one_off_costs,
        interest_rate=interest_rate,
        loan_term_years=loan_term_years,
        monthly_rent=monthly_rent,
        monthly_expenses=monthly_expenses,
        vacancy_months=vacancy_months,
        tax_rate=tax_rate,
        appreciation_rate=appreciation_rate,
        rent_growth_rate=rent_growth_rate,
        holding_period=holding_period,
        etf_comparison=etf_comparison,
        etf_return=etf_return,
        initial_fx_rate=initial_fx_rate,
        fx_appreciation=fx_appreciation,
        time_test_vars=time_test_config,
        sale_fee_percent=sale_fee_percent
    )

    # Rozbalení výsledků pro UI
    irr = metrics['irr']
    total_profit = metrics['total_profit']
    etf_irr = metrics['etf_irr']
    monthly_cashflow = metrics['monthly_cashflow_y1']
    tax_paid_y1 = metrics['tax_paid_y1']
    capital_gains_tax = metrics['capital_gains_tax']
    initial_investment = metrics['initial_investment']
    
    # Series (časové řady)
    series = metrics['series']
    property_values = series['property_values']
    mortgage_balances = series['mortgage_balances']
    yearly_cashflows_arr = series['cashflows']
    etf_values_czk = series['etf_values']
    etf_cashflows_arr = series['etf_cashflows']

    # --- Dopočítáváme pouze věci specifické pro UI zobrazení ---
    
    # 1. Splátka hypotéky (pouze pro zobrazení v metrikách nahoře)
    if mortgage_amount > 0:
        monthly_rate_display = (interest_rate / 100) / 12
        num_payments_display = loan_term_years * 12
        monthly_mortgage_payment = npf.pmt(monthly_rate_display, num_payments_display, -mortgage_amount)
    else:
        monthly_mortgage_payment = 0

    # 2. Metriky Year 1
    annual_gross_rent = monthly_rent * (12 - vacancy_months)
    annual_expenses_total = monthly_expenses * 12
    # Cash-on-Cash
    annual_cashflow_year1 = monthly_cashflow * 12
    cash_on_cash = (annual_cashflow_year1 / initial_investment) * 100 if initial_investment > 0 else 0
    # LTV
    ltv = (mortgage_amount / purchase_price) * 100 if purchase_price > 0 else 0

    # 3. Odvozené časové řady pro grafy
    # Equity = Hodnota - Dluh
    equity_values = [val - dept for val, dept in zip(property_values, mortgage_balances)]

    # 4. Finální hodnoty pro reporty
    sale_price = property_values[-1]
    final_mortgage_balance = mortgage_balances[-1]
    
    # Cistý výnos z prodeje (Net Sale Proceeds)
    # Známe: total_profit = total_cf_sum + sale_proceeds_net - initial_investment
    # Tedy: total_cf_sum = total_profit - sale_proceeds_net + initial_investment
    # Pozn: V calculations se sale_proceeds počítá čisté. Vraťme se k logice calculations.
    # sale_proceeds v metrikách už JE net. Ale calculations je neobsahuje samostatně ve výstupu (jen v cashflows a total_profit).
    # Rekonstrukce dle calculations logiky:
    final_sale_fee = sale_price * (sale_fee_percent / 100.0)
    sale_proceeds_net = sale_price - final_mortgage_balance - final_sale_fee - capital_gains_tax
    total_cf_sum = total_profit - sale_proceeds_net + initial_investment

    # ETF Metriky pro tabulky
    final_etf_value_czk = 0
    etf_profit = 0
    etf_total_invested_czk = 0
    
    if etf_comparison and len(etf_values_czk) > 0:
        final_etf_value_czk = etf_values_czk[-1]
        
        # Celkem investováno do ETF = Initial + Suma(-Contributions)
        # Contributions jsou v etf_cashflows_arr[1:-1] a castecne v [-1]
        # Jednodušší: Profit = Final Value - Total Invested
        # Známe IRR a toky, ale Total Invested není přímo v metrics.
        # Můžeme sečíst záporné toky v etf_cashflows_arr (kromě té "fiktivní" finální, kterou tam možná calculations dává, ale calculations vrací raw pole?)
        # Calculations: etf_cashflows_arr[-1] += final_etf_value_czk.
        # Takže odečteme final value od sumy toků, abychom dostali jen investice (které jsou záporné).
        sum_of_flows = sum(etf_cashflows_arr)
        # sum_of_flows = (-Invested) + FinalValue
        # Invested = FinalValue - sum_of_flows
        etf_total_invested_czk = final_etf_value_czk - sum_of_flows
        
        etf_profit = final_etf_value_czk - etf_total_invested_czk
        etf_roi = (etf_profit / etf_total_invested_czk) * 100 if etf_total_invested_czk > 0 else 0

    if capital_gains_tax > 0:
        st.info(f"ℹ️ Uplatněna daň ze zisku ({tax_rate} %) ve výši **{capital_gains_tax/1_000_000:.2f} mil. Kč** (nesplněn časový test {time_test_years} let).")

except Exception as e:
    st.error(f"Chyba ve výpočtu: {e}")
    st.stop()
    etf_profit = final_etf_value_czk - etf_total_invested_czk
    etf_roi = (etf_profit / etf_total_invested_czk) * 100 if etf_total_invested_czk > 0 else 0


# --- Zobrazení ---

# Hlavní přehled (Upraveno s lepším vysvětlením)
st.subheader("📊 Klíčové Metriky Nemovitosti")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(label="Měsíční Cashflow", value=f"{int(monthly_cashflow):,} Kč", delta_color="normal")
    st.markdown("<small style='color: grey'>Kolik vám měsíčně zbyde (nebo musíte doplatit) po zaplacení všeho.</small>", unsafe_allow_html=True)

with col2:
    st.metric(label="Měsíční splátka", value=f"{int(monthly_mortgage_payment):,} Kč")
    st.markdown(f"<small style='color: grey'>Hypotéka na {mortgage_amount/1_000_000:.2f} mil. Kč.</small>", unsafe_allow_html=True)

with col3:
    st.metric(label="LTV Ratio", value=f"{ltv:.1f} %")
    st.markdown("<small style='color: grey'>Kolik % ceny bytu vám půjčila banka.</small>", unsafe_allow_html=True)

with col4:
    st.metric(label="Cash-on-Cash Return", value=f"{cash_on_cash:.1f} %")
    st.markdown("<small style='color: grey'>Kolik % z vašich vložených peněz se vám vrátí každý rok jen z nájmu.</small>", unsafe_allow_html=True)

with col5:
    st.metric(label="Levered IRR (Roční)", value=f"{irr:.2f} %")
    st.markdown("<small style='color: grey'>Reálný roční úrok vašich peněz vč. prodeje a zhodnocení.</small>", unsafe_allow_html=True)

st.divider()

st.divider()

# Záložky pro různé pohledy
tab1, tab2, tab3, tab4 = st.tabs(["📈 Analýza a Grafy", "📊 Data a Cashflow", "⚖️ Porovnání s ETF", "🎲 Monte Carlo"])

with tab1:
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

with tab2:
    st.subheader("Detailní roční cashflow")
    
    # Vytvoření detailní tabulky
    data_dict = {
        "Rok": range(1, holding_period + 1),
        "Nemovitost Hodnota": [int(x) for x in property_values],
        "Dluh": [int(x) for x in mortgage_balances],
        "Equity": [int(x) for x in equity_values],
        "Roční CF Nemovitost": [int(x) for x in yearly_cashflows_arr[1:holding_period+1]] # Bez finálního prodeje pro přehlednost? Ne, yearly_cashflows_arr[-1] má v sobě prodej.
    }
    
    # Oprava zobrazení CF v posledním roce (chceme vidět provozní CF, ne s prodejem v tabulce cashflow?)
    # Pro tabulku je lepší vidět provozní data. year_cashflow_arr je pro IRR.
    # Musíme rekonstruovat provozní CF pro poslední rok.
    # Ale uživatel chce vidět data.
    
    df_detail = pd.DataFrame(data_dict)
    
    if etf_comparison:
        df_detail["ETF Hodnota (CZK)"] = [int(x) for x in etf_values_czk]
        # Přidat sloupec s investicí do ETF (Reinvestice)
        # Rekonstrukce z etf_cashflows_arr: [1:] jsou roční vklady (záporné).
        # Pozor: poslední prvek etf_cashflows_arr má přičtenou finální hodnotu.
        
        etf_investments = [-int(x) for x in etf_cashflows_arr[1:-1]] # Vše mezi 0 a -1
        # Poslední rok
        last_flow = etf_cashflows_arr[-1] - final_etf_value_czk # Odečteme finální hodnotu abychom dostali jen vklad
        etf_investments.append(-int(last_flow))
        
        df_detail["ETF Vklad (DCA)"] = etf_investments

    st.dataframe(df_detail, use_container_width=True)
    
    # Download button
    csv = df_detail.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Stáhnout data (CSV)",
        csv,
        "investice_data.csv",
        "text/csv",
        key='download-csv'
    )

with tab3:
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

with tab4:
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

