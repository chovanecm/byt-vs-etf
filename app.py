import streamlit as st
import numpy_financial as npf
import calculations
import uuid

# --- SESSION STATE INITIALIZATION ---
# (Portfolio init removed)

# Import components and views
from components.sidebar import render_sidebar
from views.analysis import render_analysis_tab
from views.strategy import render_strategy_tab
from views.cashflow import render_cashflow_tab
from views.comparison import render_comparison_tab
from views.monte_carlo import render_monte_carlo_tab

# Nastavení stránky
st.set_page_config(page_title="Investiční kalkulačka", layout="wide", initial_sidebar_state="auto")

# Zvětšení šířky sidebaru pomocí CSS (pouze na desktopu)
st.markdown(
    """
    <style>
    @media (min-width: 992px) {
        [data-testid="stSidebar"] {
            min-width: 500px !important;
            max-width: 500px !important;
        }
        .mobile-sidebar-hint {
            display: none;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Inicializace session state variables
if "target_ltv_input" not in st.session_state:
    st.session_state["target_ltv_input"] = 80
if "holding_period_input" not in st.session_state:
    st.session_state["holding_period_input"] = 10
if "input_type_mode" not in st.session_state:
    st.session_state["input_type_mode"] = "LTV (%)"

st.title("🏢 Analýza Investičního Bytu")

# Mobile visual hint
st.markdown(
    """
    <div class="mobile-sidebar-hint" style="background-color: #f0f2f6; color: #31333F; padding: 10px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid #ff4b4b; font-size: 0.9rem;">
        <strong>⚙️ Nastavení výpočtu</strong><br>
        Pro zadání ceny, hypotéky a dalších parametrů klikněte na šipku <strong>&gt;</strong> vlevo nahoře.
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("Interaktivní nástroj pro modelování výnosnosti investice do nemovitosti.")

# --- Render Sidebar ---
inputs = render_sidebar()

# Unpack inputs needed for top-level calculations
purchase_price = inputs['purchase_price']
down_payment = inputs['down_payment']
mortgage_amount = inputs['mortgage_amount']
one_off_costs = inputs['one_off_costs']
interest_rate = inputs['interest_rate']
loan_term_years = inputs['loan_term_years']
monthly_rent = inputs['monthly_rent']
monthly_expenses = inputs['monthly_expenses']
vacancy_months = inputs['vacancy_months']
tax_rate = inputs['tax_rate']
appreciation_rate = inputs['appreciation_rate']
rent_growth_rate = inputs['rent_growth_rate']
holding_period = inputs['holding_period']
etf_comparison = inputs['etf_comparison']
etf_return = inputs['etf_return']
initial_fx_rate = inputs['initial_fx_rate']
fx_appreciation = inputs['fx_appreciation']
time_test_config = inputs['time_test_config']
sale_fee_percent = inputs['sale_fee_percent']
general_inflation_rate = inputs.get('general_inflation_rate', 2.0)

# --- Výpočty ---
try:
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
        sale_fee_percent=sale_fee_percent,
        general_inflation_rate=general_inflation_rate
    )

    # Rozbalení výsledků pro UI
    irr = metrics['irr']
    total_profit = metrics['total_profit']
    monthly_cashflow = metrics['monthly_cashflow_y1']
    capital_gains_tax = metrics['capital_gains_tax']
    initial_investment = metrics['initial_investment']
    
    # Series (časové řady)
    series = metrics['series']
    property_values = series['property_values']
    mortgage_balances = series['mortgage_balances']
    yearly_cashflows_arr = series['cashflows']
    etf_values_czk = series['etf_values']
    etf_cashflows_arr = series['etf_cashflows']

    # --- Dopočítáváme pouze věci specifické pro UI zobrazení (Derived Metrics) ---
    derived_metrics = {}

    # 1. Splátka hypotéky (pouze pro zobrazení v metrikách nahoře)
    if mortgage_amount > 0:
        monthly_rate_display = (interest_rate / 100) / 12
        num_payments_display = loan_term_years * 12
        monthly_mortgage_payment = npf.pmt(monthly_rate_display, num_payments_display, -mortgage_amount)
    else:
        monthly_mortgage_payment = 0
    derived_metrics['monthly_mortgage_payment'] = monthly_mortgage_payment

    # 2. Metriky Year 1
    annual_cashflow_year1 = monthly_cashflow * 12
    cash_on_cash = (annual_cashflow_year1 / initial_investment) * 100 if initial_investment > 0 else 0
    ltv = (mortgage_amount / purchase_price) * 100 if purchase_price > 0 else 0
    derived_metrics['cash_on_cash'] = cash_on_cash
    derived_metrics['ltv'] = ltv

    # 3. Odvozené časové řady pro grafy
    # Equity = Hodnota - Dluh
    equity_values = [val - dept for val, dept in zip(property_values, mortgage_balances)]
    derived_metrics['equity_values'] = equity_values

    # 4. Finální hodnoty pro reporty
    sale_price = property_values[-1]
    final_mortgage_balance = mortgage_balances[-1]
    
    # Cistý výnos z prodeje (Net Sale Proceeds)
    final_sale_fee = sale_price * (sale_fee_percent / 100.0)
    sale_proceeds_net = sale_price - final_mortgage_balance - final_sale_fee - capital_gains_tax
    total_cf_sum = total_profit - sale_proceeds_net + initial_investment
    
    derived_metrics['sale_proceeds_net'] = sale_proceeds_net
    derived_metrics['total_cf_sum'] = total_cf_sum
    
    # ROI
    roi = (total_profit / initial_investment) * 100 if initial_investment > 0 else 0
    derived_metrics['roi'] = roi

    # ETF Metriky pro tabulky
    final_etf_value_czk = 0
    etf_profit = 0
    etf_total_invested_czk = 0
    
    if etf_comparison and len(etf_values_czk) > 0:
        final_etf_value_czk = etf_values_czk[-1]
        sum_of_flows = sum(etf_cashflows_arr)
        etf_total_invested_czk = final_etf_value_czk - sum_of_flows
        etf_profit = final_etf_value_czk - etf_total_invested_czk
        etf_roi = (etf_profit / etf_total_invested_czk) * 100 if etf_total_invested_czk > 0 else 0
    else:
        etf_profit = 0
        etf_roi = 0

    derived_metrics['final_etf_value_czk'] = final_etf_value_czk
    derived_metrics['etf_total_invested_czk'] = etf_total_invested_czk
    derived_metrics['etf_profit'] = etf_profit
    derived_metrics['etf_roi'] = etf_roi

    if capital_gains_tax > 0:
        t_years = time_test_config['years']
        st.info(f"ℹ️ Uplatněna daň ze zisku ({tax_rate} %) ve výši **{capital_gains_tax/1_000_000:.2f} mil. Kč** (nesplněn časový test {t_years} let).")

except Exception as e:
    st.error(f"Chyba ve výpočtu: {e}")
    st.stop()


# --- Zobrazení ---

# --- DASHBOARD (KISS Summary - Above Tabs) ---
st.markdown("### 📊 Rychlý přehled: Vyplatí se to?")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="💰 Měsíční Cashflow",
        value=f"{int(monthly_cashflow):,} Kč",
        delta="Do kapsy" if monthly_cashflow > 0 else "Dotujete",
        delta_color="normal" if monthly_cashflow > 0 else "inverse",
        help="To, co vás nejvíc zajímá. Zbyde vám na kávu, nebo musíte sáhnout do výplaty?"
    )
    
with kpi2:
    st.metric(
        label="📈 Roční výnos (IRR)",
        value=f"{irr:.2f} %",
        help="Internal Rate of Return - Skutečný 'úrok', který vám tato investice vydělává (včetně růstu ceny)."
    )
    
with kpi3:
    st.metric(
        label="🏦 Čistý zisk (za celou dobu)",
        value=f"{total_profit / 1_000_000:.2f} mil. Kč",
        help=f"O tolik budete bohatší za {holding_period} let (po zaplacení banky, daní a oprav)."
    )
    
with kpi4:
     # Verdikt: Vyplatí se to?
     # Kombinace Výnosu a Benchmarku
     is_positive_cf = monthly_cashflow >= 0
     beats_benchmark = irr > (etf_return if etf_comparison else 0)
     
     if beats_benchmark and is_positive_cf:
         st.success("✅ **ANO, VYPLATÍ SE**")
         st.caption("Investice vydělává více než benchmark a platí se sama.")
     elif beats_benchmark and not is_positive_cf:
         st.warning("⚠️ **ANO, ALE DOTUJETE**")
         st.caption(f"Vyděláte, ale měsíčně doplácíte {int(abs(monthly_cashflow)):,} Kč.")
     elif not beats_benchmark and is_positive_cf:
         st.info("🤔 **NIŽŠÍ VÝNOS**")
         st.caption("Byt se sice zaplatí sám, ale vaše alternativa (např. ETF) by vydělala víc.")
     else:
         st.error(f"⛔ **NEVYPLATÍ SE**")
         st.caption("Proděláváte na provozu a výnos je nižší než benchmark.")

st.divider()

# --- TABS ---
t_analysis, t_cashflow, t_strategy, t_compare, t_monte = st.tabs([
    "📊 Analýza (Draft)", 
    "💰 Cashflow Detail", 
    "🔮 Strategie & Rozhodování", 
    "⚖️ Porovnání", 
    "🎲 Monte Carlo (Riziko)"
])

with t_analysis:
    # Hlavní přehled (Původní detailní metriky)
    st.subheader("Detailní Metriky Nemovitosti")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(label="Měsíční Cashflow", value=f"{int(monthly_cashflow):,} Kč", delta_color="normal")
        st.caption("Čistý měsíční tok peněz")

    with col2:
        st.metric(label="Měsíční splátka", value=f"{int(monthly_mortgage_payment):,} Kč")
        st.caption(f"Hypotéka na {mortgage_amount/1_000_000:.2f} mil.")

    with col3:
        st.metric(label="LTV (Páka)", value=f"{ltv:.1f} %")
        st.caption("Podíl cizích peněz")

    with col4:
        st.metric(label="Cash-on-Cash", value=f"{cash_on_cash:.1f} %")
        st.caption("Výnos z nájmu vůči vkladu")

    with col5:
        st.metric(label="Levered IRR (Roční)", value=f"{irr:.2f} %")
        st.caption("Reálný roční úrok vašich peněz vč. prodeje a zhodnocení.")

    st.divider()

    render_analysis_tab(inputs, metrics, derived_metrics)
    
with t_cashflow:
    render_cashflow_tab(inputs, metrics, derived_metrics)

with t_strategy:
    render_strategy_tab(inputs, metrics, derived_metrics)
    
with t_compare:
    render_comparison_tab(inputs, metrics, derived_metrics)
    
with t_monte:
    render_monte_carlo_tab(inputs, metrics, derived_metrics)


