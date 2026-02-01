import json
import os
import streamlit as st

SCENARIO_FILE = "scenarios.json"

def load_scenarios():
    """Načte všechny scénáře ze souboru."""
    if not os.path.exists(SCENARIO_FILE):
        return {}
    
    try:
        with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_scenario(name, params):
    """Uloží nový scénář nebo přepíše existující."""
    scenarios = load_scenarios()
    scenarios[name] = params
    
    with open(SCENARIO_FILE, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=4)

def delete_scenario(name):
    """Smaže scénář."""
    scenarios = load_scenarios()
    if name in scenarios:
        del scenarios[name]
        with open(SCENARIO_FILE, "w", encoding="utf-8") as f:
            json.dump(scenarios, f, ensure_ascii=False, indent=4)
        return True
    return False

def get_current_inputs():
    """Vrátí slovník všech relevantních vstupů ze session state."""
    # Seznam klíčů, které chceme ukládat
    keys_to_save = [
        "purchase_price_m", "input_type_radio", "target_ltv_slider", 
        "down_payment_m", "one_off_costs", "interest_rate", "loan_term_years",
        "monthly_rent", "monthly_expenses", "vacancy_months", "tax_rate",
        "appreciation_rate", "rent_growth_rate", "holding_period_slider",
        "etf_comparison", "etf_return", "initial_fx_rate", "fx_appreciation",
        "time_test_enabled", "time_test_years", "sale_fee_percent"
    ]
    
    data = {}
    for key in keys_to_save:
        if key in st.session_state:
            data[key] = st.session_state[key]
    return data

def apply_scenario(scenario_data):
    """Aplikuje data scénáře do session state."""
    for key, value in scenario_data.items():
        st.session_state[key] = value
