import streamlit as st
import numpy_financial as npf
import calculations

# Import components and views
from components.sidebar import render_sidebar
from views.analysis import render_analysis_tab
from views.strategy import render_strategy_tab
from views.cashflow import render_cashflow_tab
from views.comparison import render_comparison_tab
from views.monte_carlo import render_monte_carlo_tab

# Nastavení stránky
st.set_page_config(page_title="Investiční kalkulačka", layout="wide", initial_sidebar_state="expanded")

# Zvětšení šířky sidebaru pomocí CSS (pouze na desktopu)
st.markdown(
    """
    <style>
    @media (min-width: 992px) {
        [data-testid="stSidebar"] {
            min-width: 500px;
            max-width: 500px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Inicializace session state variables used in sidebar
if "target_ltv_input" not in st.session_state:
    st.session_state["target_ltv_input"] = 80
if "holding_period_input" not in st.session_state:
    st.session_state["holding_period_input"] = 10
if "input_type_mode" not in st.session_state:
    st.session_state["input_type_mode"] = "LTV (%)"

st.title("🏢 Analýza Investičního Bytu")
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
        sale_fee_percent=sale_fee_percent
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

# Záložky pro různé pohledy
tab1, tab_strat, tab2, tab3, tab4 = st.tabs(["📈 Analýza a Grafy", "🔮 Strategie a Rozhodování", "📊 Data a Cashflow", "⚖️ Porovnání s ETF", "🎲 Monte Carlo"])

with tab1:
    render_analysis_tab(inputs, metrics, derived_metrics)

with tab_strat:
    render_strategy_tab(inputs, metrics, derived_metrics)
    
with tab2:
    render_cashflow_tab(inputs, metrics, derived_metrics)

with tab3:
    render_comparison_tab(inputs, metrics, derived_metrics)

with tab4:
    render_monte_carlo_tab(inputs)

