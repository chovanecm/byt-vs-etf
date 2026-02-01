import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go

# Nastavení stránky
st.set_page_config(page_title="Investiční kalkulačka", layout="wide", initial_sidebar_state="expanded")

# CSS pro tmavý režim (Streamlit má defaultní podporu, ale můžeme doladit)
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏢 Analýza Investičního Bytu")
st.markdown("Interaktivní nástroj pro modelování výnosnosti investice do nemovitosti.")

# --- Sidebar Vstupy ---
st.sidebar.header("Parametry investice")

# Cena nemovitosti
purchase_price_m = st.sidebar.number_input("Kupní cena bytu (v mil. Kč)", min_value=1.0, value=5.0, step=0.1)
purchase_price = purchase_price_m * 1_000_000

# Vlastní kapitál
default_down_payment = int(purchase_price * 0.2) # Default 20%
down_payment = st.sidebar.number_input("Vlastní kapitál (Kč)", min_value=0, max_value=int(purchase_price), value=default_down_payment, step=100_000)

mortgage_amount = purchase_price - down_payment
if mortgage_amount < 0:
    mortgage_amount = 0

# Hypotéka
st.sidebar.subheader("Hypotéka")
interest_rate = st.sidebar.number_input("Úroková sazba (%)", min_value=0.0, value=5.4, step=0.1)
loan_term_years = st.sidebar.number_input("Doba splácení (roky)", min_value=1, max_value=40, value=30, step=1)

# Příjmy a Výdaje
st.sidebar.subheader("Cashflow")
monthly_rent = st.sidebar.number_input("Měsíční nájemné (Kč)", min_value=0, value=18_000, step=500)
monthly_expenses = st.sidebar.number_input("Měsíční náklady (Kč)", min_value=0, value=3_500, step=100, help="Fond oprav, pojištění, správa, daň z nemovitosti (rozpočítaná)")

# Projekce
st.sidebar.subheader("Projekce vývoje")
appreciation_rate = st.sidebar.slider("Odhadovaný roční růst ceny (%)", 0.0, 10.0, 3.0, 0.1)
holding_period = st.sidebar.slider("Doba držení investice (roky)", 1, 30, 10, 1)


# --- Výpočty ---

# 1. Splátka hypotéky
if mortgage_amount > 0:
    monthly_rate = (interest_rate / 100) / 12
    num_payments = loan_term_years * 12
    monthly_mortgage_payment = npf.pmt(monthly_rate, num_payments, -mortgage_amount)
else:
    monthly_mortgage_payment = 0

# 2. Měsíční Cashflow
monthly_cashflow = monthly_rent - monthly_mortgage_payment - monthly_expenses
annual_cashflow = monthly_cashflow * 12

# 3. Metriky výnosnosti
annual_rent = monthly_rent * 12
annual_expenses = monthly_expenses * 12
net_yield = ((annual_rent - annual_expenses) / purchase_price) * 100 if purchase_price > 0 else 0

cash_on_cash = (annual_cashflow / down_payment) * 100 if down_payment > 0 else 0

# 4. Vývoj v čase (Projekce)

# Připravíme data pro graf a IRR
years = list(range(holding_period + 1))
property_values = []
mortgage_balances = []
equity_values = []
cumulative_cashflows = [0]
yearly_cashflows_arr = [-down_payment] # CF pro rok 0 (investice)

current_balance = mortgage_amount
current_value = purchase_price
total_cf_sum = 0

for year in range(1, holding_period + 1):
    # a) Hodnota nemovitosti
    current_value = purchase_price * ((1 + appreciation_rate / 100) ** year)
    property_values.append(current_value)

    # b) Zůstatek hypotéky
    # Pro zjednodušení počítáme zůstatek na konci roku
    # Zůstatek se sníží o (Splátka - Úrok) * 12, ale přesněji přes FV funkci
    if mortgage_amount > 0:
        # Zůstatek po 'year' letech
        period_months = year * 12
        if period_months >= num_payments:
             rem_balance = 0
        else:
             rem_balance = npf.fv(monthly_rate, period_months, monthly_mortgage_payment, -mortgage_amount)
        if rem_balance < 0: rem_balance = 0 # Pro jistotu
    else:
        rem_balance = 0
    
    mortgage_balances.append(rem_balance)
    
    # c) Equity
    equity = current_value - rem_balance
    equity_values.append(equity)

    # d) Cashflow pro IRR
    # Pro jednoduchost předpokládáme konstantní nájem (nebo bychom mohli přidat růst nájmu)
    # Zde: roční cashflow
    curr_annual_cf = annual_cashflow 
    yearly_cashflows_arr.append(curr_annual_cf)
    
    total_cf_sum += curr_annual_cf
    cumulative_cashflows.append(total_cf_sum)

# Přidání prodejní ceny do posledního roku cashflow pro IRR
sale_price = property_values[-1]
final_mortgage_balance = mortgage_balances[-1]
# Zisk z prodeje (očištěno o hypotéku)
sale_proceeds = sale_price - final_mortgage_balance

# Upravíme poslední tok v poli pro IRR
yearly_cashflows_arr[-1] += sale_proceeds

# Výpočet IRR
irr = npf.irr(yearly_cashflows_arr) * 100

# Celkový profit
total_profit = total_cf_sum + sale_proceeds - down_payment # CF + Equity na konci - Počáteční vklad

# --- Zobrazení ---

# Hlavní přehled
st.subheader("📊 Klíčové Metriky")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Měsíční Cashflow", value=f"{int(monthly_cashflow):,} Kč", delta_color="normal")
    st.caption(f"Splátka: {int(monthly_mortgage_payment):,} Kč")

with col2:
    st.metric(label="Čistý výnos (Net Yield)", value=f"{net_yield:.2f} %")
    st.caption("Roční zisk / Cena bytu")

with col3:
    st.metric(label="Cash-on-Cash Return", value=f"{cash_on_cash:.1f} %")
    st.caption("Roční CF / Vlastní zdroje")

with col4:
    st.metric(label="Levered IRR (Roční)", value=f"{irr:.2f} %")
    st.caption("Vč. prodeje a zhodnocení")

st.info(f"""
**Vysvětlení IRR:** Levered IRR (Vnitřní výnosové procento s pákou) představuje průměrné roční zhodnocení vašich vlastních investovaných prostředků ({int(down_payment):,} Kč). 
Zahrnuje pravidelný měsíční cashflow i konečný zisk z prodeje nemovitosti po {holding_period} letech.
""")

st.divider()

# Grafy
st.subheader("📈 Vývoj v čase")

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

fig.update_layout(
    title=f"Hodnota bytu vs. Dluh ({holding_period} let)",
    xaxis_title="Rok",
    yaxis_title="Hodnota (Kč)",
    legend_title="Legenda",
    hovermode="x unified",
    height=450
)

st.plotly_chart(fig, use_container_width=True)

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
    roi = (total_profit / down_payment) * 100 if down_payment > 0 else 0
    st.markdown(f"""
    **Ziskovost:**
    - Kumulované cashflow (příjmy z nájmu): **{int(total_cf_sum):,} Kč**
    - **Celkový čistý zisk:** **{int(total_profit):,} Kč**
    - ROI (Celková návratnost): **{roi:.1f} %**
    """)

