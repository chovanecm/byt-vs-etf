import json
import os
import streamlit as st

# Functionality for local file operations (might not be persistent in cloud)
SCENARIO_FILE = "scenarios.json"

def load_scenarios():
    """Načte všechny scénáře ze souboru (lokální)."""
    if not os.path.exists(SCENARIO_FILE):
        return {}
    
    try:
        with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_scenario(name, params):
    """Uloží nový scénář nebo přepíše existující (lokální)."""
    scenarios = load_scenarios()
    scenarios[name] = params
    
    with open(SCENARIO_FILE, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=4)

def delete_scenario(name):
    """Smaže scénář (lokální)."""
    scenarios = load_scenarios()
    if name in scenarios:
        del scenarios[name]
        with open(SCENARIO_FILE, "w", encoding="utf-8") as f:
            json.dump(scenarios, f, ensure_ascii=False, indent=4)
        return True
    return False

# Functionality for State Management (Cloud/File Independent)

def get_current_inputs():
    """Vrátí slovník všech JSON-serializovatelných vstupů ze session state."""
    data = {}
    
    # Klíče, které explicitně nechceme ukládat (např. výsledky importu, nahrané soubory)
    excluded_keys = {"uploaded_scenario_json", "import_status", "opt_result", "FormSubmitter"}

    for key, value in st.session_state.items():
        if key in excluded_keys:
            continue
            
        # Ukládáme jen základní datové typy
        if isinstance(value, (str, int, float, bool, list, dict, tuple, type(None))):
            data[key] = value
            
    return data

def apply_scenario(scenario_data):
    """Aplikuje data scénáře do session state."""
    if not scenario_data:
        return
        
    for key, value in scenario_data.items():
        # U range slideru musíme zajistit, že hodnota je tuple (v JSON se ukládá jako list)
        if key == "opt_ltv_range" and isinstance(value, list):
            value = tuple(value)
            
        st.session_state[key] = value

def export_json():
    """Vrátí JSON string aktuální konfigurace."""
    data = get_current_inputs()
    return json.dumps(data, ensure_ascii=False, indent=4)

def load_from_json(json_str):
    """Načte konfiguraci z JSON stringu."""
    try:
        data = json.loads(json_str)
        apply_scenario(data)
        return True
    except json.JSONDecodeError:
        return False
