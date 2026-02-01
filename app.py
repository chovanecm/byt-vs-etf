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
                res = calculations.calculate_metrics(
                    purchase_price=purchase_price,
                    down_payment=try_down_payment,
                    one_off_costs=one_off_costs,
                    interest_rate=interest_rate,
                    loan_term_years=loan_term_years,
                    monthly_rent=monthly_rent,
                    monthly_expenses=monthly_expenses,
                    vacancy_months=vacancy_months,
                    tax_rate=15.0, 
                    appreciation_rate=appreciation_rate,
                    rent_growth_rate=rent_growth_rate,
                    holding_period=try_year,
                    etf_comparison=False,
                    etf_return=0,
                    initial_fx_rate=25,
                    fx_appreciation=0
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

# 1. Splátka hypotéky
if mortgage_amount > 0:
    monthly_rate = (interest_rate / 100) / 12
    num_payments = loan_term_years * 12
    monthly_mortgage_payment = npf.pmt(monthly_rate, num_payments, -mortgage_amount)
else:
    monthly_mortgage_payment = 0

# 2. Měsíční Cashflow
# Zohlednění neobsazenosti: (Nájem * (12 - neobsazenost) - Náklady * 12 - Splátky * 12) / 12 ... přepočteno na průměrný měsíc
annual_gross_rent = monthly_rent * (12 - vacancy_months)
annual_expenses_total = monthly_expenses * 12
annual_mortgage_payment = monthly_mortgage_payment * 12

annual_cashflow_year1 = annual_gross_rent - annual_mortgage_payment - annual_expenses_total
monthly_cashflow = annual_cashflow_year1 / 12 # Průměrné měsíční CF v prvním roce

# 3. Metriky výnosnosti
net_yield = ((annual_gross_rent - annual_expenses_total) / (purchase_price + one_off_costs)) * 100 if purchase_price > 0 else 0

initial_investment = down_payment + one_off_costs
cash_on_cash = (annual_cashflow_year1 / initial_investment) * 100 if initial_investment > 0 else 0

# LTV (Loan-to-Value)
ltv = (mortgage_amount / purchase_price) * 100 if purchase_price > 0 else 0

# Alternativní investice do ETF
if etf_comparison:
    # Přepočet počáteční investice do EUR
    etf_balance_eur = initial_investment / initial_fx_rate
    etf_values_czk = []
    
    # Pro IRR ETF
    etf_cashflows_arr = [-initial_investment] # T0: Počáteční vklad v CZK
    etf_total_invested_czk = initial_investment

# 4. Vývoj v čase (Projekce)

# Připravíme data pro graf a IRR
years = list(range(holding_period + 1))
property_values = []
mortgage_balances = []
equity_values = []
cumulative_cashflows = [0]
yearly_cashflows_arr = [-initial_investment] # CF pro rok 0 (vč. nákladů nákupu)

current_balance = mortgage_amount
current_value = purchase_price
total_cf_sum = 0
current_monthly_rent = monthly_rent
current_monthly_expenses = monthly_expenses

for year in range(1, holding_period + 1):
    # a) Hodnota nemovitosti
    current_value = purchase_price * ((1 + appreciation_rate / 100) ** year)
    property_values.append(current_value)

    # Indexace nájmu a nákladů
    if year > 1: # První rok už máme nastavený, rosteme od druhého
        current_monthly_rent *= (1 + rent_growth_rate / 100)
        current_monthly_expenses *= (1 + rent_growth_rate / 100)

    # Cashflow pro daný rok
    curr_annual_gross_rent = current_monthly_rent * (12 - vacancy_months)
    curr_annual_expenses = current_monthly_expenses * 12
    curr_annual_cf = curr_annual_gross_rent - annual_mortgage_payment - curr_annual_expenses
    
    yearly_cashflows_arr.append(curr_annual_cf)
    
    total_cf_sum += curr_annual_cf
    cumulative_cashflows.append(total_cf_sum)

    # b) Zůstatek hypotéky
    if mortgage_amount > 0:
        period_months = year * 12
        if period_months >= num_payments:
             rem_balance = 0
        else:
             rem_balance = npf.fv(monthly_rate, period_months, monthly_mortgage_payment, -mortgage_amount)
        if rem_balance < 0: rem_balance = 0
    else:
        rem_balance = 0
    
    mortgage_balances.append(rem_balance)
    
    # c) Equity
    equity = current_value - rem_balance
    equity_values.append(equity)
    
    # d) ETF Výpočet (s reinvestováním dotací)
    if etf_comparison:
        # 1. Zhodnocení EUR zůstatku za tento rok
        etf_balance_eur *= (1 + etf_return / 100)
        
        # 2. Reinvestice (DCA): Pokud nemovitost musím dotovat (CF < 0), 
        # v alternativním scénáři tyto peníze investuji do ETF.
        year_contribution_czk = 0
        if curr_annual_cf < 0:
            year_contribution_czk = abs(curr_annual_cf)
            
            # Přepočet dotace na EUR podle aktuálního kurzu v daném roce
            current_fx_rate = initial_fx_rate * ((1 + fx_appreciation / 100) ** year)
            contribution_eur = year_contribution_czk / current_fx_rate
            
            # Přidání k zůstatku (předpoklad: investováno v průběhu roku, pro zjednodušení na konci)
            etf_balance_eur += contribution_eur
            etf_total_invested_czk += year_contribution_czk
        
        # 3. Přepočet celkové hodnoty zpět do CZK pro graf
        current_fx_rate_end = initial_fx_rate * ((1 + fx_appreciation / 100) ** year)
        etf_value_now_czk = etf_balance_eur * current_fx_rate_end
        etf_values_czk.append(etf_value_now_czk)
        
        # 4. Záznam toku pro IRR (-výdaj)
        etf_cashflows_arr.append(-year_contribution_czk)


# Přidání prodejní ceny do posledního roku cashflow pro IRR
sale_price = property_values[-1]
final_mortgage_balance = mortgage_balances[-1]
sale_proceeds = sale_price - final_mortgage_balance

# Upravíme poslední tok v poli pro IRR
yearly_cashflows_arr[-1] += sale_proceeds
irr = npf.irr(yearly_cashflows_arr) * 100
total_profit = total_cf_sum + sale_proceeds - initial_investment # Zde pozor: total_cf_sum už obsahuje ty záporné toky, takže je to OK.

# Dopočet ETF metrik
if etf_comparison:
    final_etf_value_czk = etf_values_czk[-1]
    
    # Pro IRR ETF musíme na konec přidat finální hodnotu (jako "prodej" portfolia)
    # Pozor: etf_cashflows_arr má zatím jen vklady [-Init, -Contrib1, -Contrib2...]
    # Musíme k poslednímu prvku (nebo jako nový prvek na konci) přidat výběr celé sumy.
    # Aby to sedělo časově s nemovitostí:
    # yearly_cashflows_arr má délku N+1 (0..N).
    # etf_cashflows_arr má také mít délku N+1.
    
    etf_cashflows_arr[-1] += final_etf_value_czk # Přičtení finální hodnoty k poslednímu roku
    
    etf_irr = npf.irr(etf_cashflows_arr) * 100
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
tab1, tab2, tab3 = st.tabs(["📈 Analýza a Grafy", "📊 Data a Cashflow", "⚖️ Porovnání s ETF"])

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

    fig.add_trace(go.Scatter(
        x=df_chart["Rok"], 
        y=df_chart["Hodnota nemovitosti"],
        mode='lines',
        name='Hodnota nemovitosti',
        line=dict(color='#4CAF50', width=3)
    ))

    fig.add_trace(go.Scatter(
        x=df_chart["Rok"], 
        y=df_chart["Zůstatek hypotéky"],
        mode='lines',
        name='Zůstatek hypotéky',
        line=dict(color='#FF5252', width=3, dash='dash'),
        fill='tozeroy' # Vyplní oblast pod křivkou
    ))

    # Přidání ETF do grafu
    if etf_comparison:
        fig.add_trace(go.Scatter(
            x=df_chart["Rok"], 
            y=etf_values_czk,
            mode='lines',
            name='Hodnota ETF (IWDA v CZK)',
            line=dict(color='#2196F3', width=3, dash='dot')
        ))

    fig.update_layout(
        title=f"Porovnání investic v čase ({holding_period} let)",
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
        - Čistá hodnota při prodeji: **{int(sale_proceeds):,} Kč**
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
                f"{int(initial_investment + abs(sum(x for x in yearly_cashflows_arr if x < 0) - initial_investment if yearly_cashflows_arr[0] < 0 else 0)):,} Kč", # Zjednodušený odhad invested
                f"{int(sale_proceeds):,} Kč",
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

