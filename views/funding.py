import streamlit as st

def render_funding_section(inputs):
    """
    Vizualizace struktury financování (Kupní cena vs. Vlastní zdroje vs. Úvěr).
    """
    st.markdown("### 🏦 Struktura Financování")

    purchase_price = inputs.get('purchase_price', 0)
    down_payment = inputs.get('down_payment', 0)
    one_off_costs = inputs.get('one_off_costs', 0)
    
    loan_amount = max(0, purchase_price - down_payment)
    total_cash_needed = down_payment + one_off_costs

    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Celková investice (Cash)", f"{int(total_cash_needed):,} Kč", help="Vlastní zdroje + Jednorázové náklady")
    
    with c2:
        st.metric("Výše úvěru", f"{int(loan_amount):,} Kč", help="Kupní cena - Vlastní zdroje")
        
    with c3:
        ltv = (loan_amount / purchase_price * 100) if purchase_price > 0 else 0
        st.metric("LTV", f"{ltv:.1f} %", help="Loan To Value (Poměr úvěru k ceně nemovitosti)")

    # Bar chart visualization of funding
    st.progress(ltv / 100)
    st.caption(f"Páka (LTV): {ltv:.1f}% cizích zdrojů")

    st.divider()
