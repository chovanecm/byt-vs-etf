import numpy_financial as npf

def calculate_mortgage_payment(loan_amount, annual_rate, years):
    """Vypočítá měsíční splátku hypotéky."""
    if loan_amount <= 0:
        return 0, 0
    
    monthly_rate = (annual_rate / 100) / 12
    num_payments = years * 12
    
    monthly_payment = npf.pmt(monthly_rate, num_payments, -loan_amount)
    return monthly_payment, monthly_rate

def update_remaining_balance(current_balance, monthly_rate, monthly_payment):
    """Vypočítá zůstatek hypotéky po roce splácení (zjednodušená FV metoda po měsících)."""
    if current_balance <= 0:
        return 0
    # 12 měsíců splácení
    balance = npf.fv(monthly_rate, 12, monthly_payment, -current_balance)
    return max(0, balance)
