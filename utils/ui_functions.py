### STREAMLIT OBJECT GENERATORS
import streamlit as st
import toml
import os
import re

import objs.plan
import utils.ui_functions
from utils.emoji_config import *

# Load configuration
def load_config():
    """Load configuration from config.toml file."""
    try:
        with open('config.toml', 'r') as f:
            return toml.load(f)
    except FileNotFoundError:
        st.error("Configuration file 'config.toml' not found!")
        return None

# Load config once
CONFIG = load_config()

def get_config_value(section, key, default=None):
    """Get a value from the config file with fallback to default."""
    if CONFIG and section in CONFIG and key in CONFIG[section]:
        return CONFIG[section][key]
    return default

def add_colorful_divider():
    """Add a colorful divider using Planaria brand colors."""
    divider_html = '''
    <hr style="
        height: 4px;
        background: linear-gradient(90deg, 
            #d2694b 0%, 
            #d2694b 20%,
            #d9a441 20%, 
            #d9a441 40%,
            #4f7c4a 40%, 
            #4f7c4a 60%,
            #4a6b8a 60%, 
            #4a6b8a 80%,
            #423721 80%, 
            #423721 100%
        );
        border: none;
        margin: 0.5rem 0;
        border-radius: 2px;
        box-shadow: 0 1px 3px rgba(66, 55, 33, 0.1);
    ">
    '''
    st.html(divider_html)

def setup_page():
    """Setup page configuration and inject CSS for all pages."""
    # Set page config with favicon and title from config
    app_title = CONFIG['app_settings']['app_title'] if CONFIG else "Planaria"
    favicon_path = CONFIG['app_settings']['favicon_path'] if CONFIG else "assets/planaria_icon.ico"
    
    st.set_page_config(
        page_title=app_title,
        page_icon=favicon_path,
        layout="wide"
    )
    
    # Load and inject custom CSS
    with open('assets/style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    

# Get defaults from config
default_start_year = CONFIG['plan_defaults']['start_year'] if CONFIG else 2025
default_n_years = CONFIG['plan_defaults']['n_years'] if CONFIG else 35
default_infl = CONFIG['plan_defaults']['inflation_rate'] if CONFIG else 0.03
default_col = CONFIG['plan_defaults']['col_raise_rate'] if CONFIG else 0.02  

# Sidebar
    
def make_sidebar():
    """Create the main sidebar with plan controls."""
    with st.sidebar:
        # Add Planaria header image at the top
        st.image('assets/planaria_header.png', use_container_width=True)
        with st.expander(label=f'{SIDEBAR_PLAN} Plan'):
            st.page_link('app.py',label=f'{SIDEBAR_NEW_LOAD} New/Load Plan')
            if st.session_state['plan'] is not None:
                st.page_link('pages/plan_and_people.py',label=f'{SIDEBAR_PEOPLE} People and Settings')
        if st.session_state['plan'] is not None:
            with st.expander(label=f'{SIDEBAR_CURRENT_STATE} Current State'):
                st.page_link('pages/income.py',label=f'{SIDEBAR_INCOME} Income')
                st.page_link('pages/assets.py',label=f'{SIDEBAR_ASSETS} Assets')
                st.page_link('pages/liabilities.py',label=f'{SIDEBAR_LIABILITIES} Liabilities')
                st.page_link('pages/expenses.py',label=f'{SIDEBAR_EXPENSES} Expenses')
            with st.expander(label=f'{SIDEBAR_FUTURE_EVENTS} Future Events'):
                st.page_link('pages/future_events.py',label=f'{SIDEBAR_FUTURE_EVENTS_LINK} Future Events')
            with st.expander(label=f'{SIDEBAR_RESULTS} Results'):
                st.page_link('pages/cash_flow.py',label=f'{SIDEBAR_CASH_FLOW} Budget/Cash Flow')
                st.page_link('pages/net_worth.py',label=f'{SIDEBAR_NET_WORTH} Net Worth')
                st.page_link('pages/ratios.py',label=f'{SIDEBAR_RATIOS} Ratio Analysis')
            st.button(f"{BUTTON_UPDATE} Update Plan",on_click=utils.ui_functions.update_plan,use_container_width=True,disabled=st.session_state['plan_updated'])
            st.button(f"{BUTTON_SAVE} Save Plan",on_click=utils.ui_functions.save_plan,use_container_width=True,disabled=st.session_state['plan_saved'])

def sidebar_buttons(logical):
    """Enable/disable sidebar buttons based on plan state."""
    st.session_state['plan_updated'] = logical
    st.session_state['plan_saved'] = logical

# Plan Functions
def set_new_plan():
    """Create a new plan with default settings."""
    st.session_state['plan'] = objs.plan.Plan(st.session_state['plan_name'],default_start_year,default_n_years,default_infl,default_col)
    sidebar_buttons(True)
    #utils.ui_functions.make_sidebar()
    st.rerun()

def save_plan():
    """Save the current plan to a JSON file."""
    if st.session_state['plan_updated'] == False:
        update_plan()
    raw_name = st.session_state['plan'].name
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', str(raw_name).strip())
    safe_name = re.sub(r'\s+', ' ', safe_name).strip()
    if safe_name == '':
        st.error("Save failed: plan name is empty or invalid.")
        return
    plan_name = safe_name
    target_path = f"saved_plans/{plan_name}.json"
    temp_path = f"{target_path}.tmp"
    try:
        payload = st.session_state['plan'].to_json_string()
        if payload is None or payload.strip() == '':
            raise ValueError("Plan serialization produced empty JSON.")
        with open(temp_path, 'w') as out:
            out.write(payload)
        os.replace(temp_path, target_path)
        st.session_state['plan_saved'] = True
    except Exception as exc:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        st.error(f"Save failed: {exc}")

def update_plan():
    """
    Update the plan by processing events and running balance/tax calculations.
    
    This is the main workhorse function that:
    1. Processes marriage events
    2. Processes expense combination events  
    3. Runs balance and tax calculations
    """
    # Apply marriage events first (sets married series and applies budget withdrawals)
    for ev in st.session_state['plan'].events:
        if ev[1] == 'Get Married':
            year = ev[0]
            payload = ev[2]
            # Set married state based on event year
            st.session_state['plan'] = st.session_state['plan'].get_married(year)
            # Apply budget withdrawals from savings sources
            budget = int(payload.get('budget', 0) or 0)
            sources = payload.get('sources', [])
            if budget > 0 and len(sources) > 0:
                total_prop = sum([float(p) for _, p in sources])
                total_prop = total_prop if total_prop != 0 else 1.0
                for asset_id, prop in sources:
                    amt = int(round(budget * (float(prop) / total_prop)))
                    asset = st.session_state['plan'].get_object_from_id(asset_id)
                    if asset is not None:
                        asset = asset.withdrawal(amt, year)
                        st.session_state['plan'] = asset.project(st.session_state['plan'])
    # Apply grouped Combine Expenses events so taxes/analytics reflect combined state
    for ev in st.session_state['plan'].events:
        if ev[1] == 'Combine Expenses':
            names = ev[2].get('names', [])
            year = ev[0]
            st.session_state['plan'] = st.session_state['plan'].combine_expenses(names, year)
    # Then compute balance and taxes
    st.session_state['plan'] = st.session_state['plan'].balance_and_tax()
    st.session_state['plan_updated'] = True


# EVENTUALLY ADD THE GENERIC ADD/UPDATE/GENERATE OBJECT FUNCTIONS HERE

