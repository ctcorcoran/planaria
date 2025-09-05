import streamlit as st 

import utils.utilities
import utils.ui_functions
import utils.plotting
from utils.emoji_config import *

# Setup page configuration and CSS
utils.ui_functions.setup_page()

#############
# FUNCTIONS #
#############

def update_display_person(key):
    st.session_state['display_person'] = st.session_state[key]

def format_name(person_id):
    if person_id == 'Joint':
        return('Joint')
    else:
        return(st.session_state['plan'].get_object_from_id(person_id).name)

def get_ratio_definitions():
    # Definitions from comments in compute_analytical_timeseries
    return {
        'liquidity_ratio': 'Represents months of emergency fund. Target: 3-6 months.',
        'after_tax_savings_ratio': 'Target: ~10%.',
        'total_savings_ratio': 'Target depends on retirement needs.',
        'current_ratio': 'Should be > 1. Approximates short-term debt coverage.',
        'debt_to_asset_ratio': 'Target: 0.3-0.6, should decrease over time.',
        'debt_to_income_ratio': 'Target: < 35%.',
        'non_mortgage_debt_service_ratio': 'Target: < 15%.',
        'household_debt_service_ratio': 'Target: < 25%.',
        'liquid_savings_to_net_worth_ratio': 'Target: ~15%.',
        'invested_assets_to_net_worth_ratio': 'Target: > 50%.',
        'solvency_ratio': 'Should increase with age (0.2 when young, 0.9 in retirement).',
        'basic_housing_ratio': 'Target: < 0.28 (or 0.33 in HCOL areas).',
        'investment_assets_to_gross_pay_ratio': 'Goal: 20:1 by retirement.'
    }

def get_ratio_latex():
    # LaTeX formulas for each ratio
    return {
        'liquidity_ratio': r"\text{Liquidity Ratio} = \frac{\text{Cash and Cash Investments}}{\text{Non-Discretionary Expenses} / 12}",
        'after_tax_savings_ratio': r"\text{After Tax Savings Ratio} = \frac{\text{Cash Savings}}{\text{After-Tax Income}}",
        'total_savings_ratio': r"\text{Total Savings Ratio} = \frac{\text{Cash Savings} + \text{Retirement Savings}}{\text{Gross Income}}",
        'current_ratio': r"\text{Current Ratio} = \frac{\text{Cash Assets}}{\text{Current Liabilities}}",
        'debt_to_asset_ratio': r"\text{Debt to Asset Ratio} = \frac{\text{Total Liabilities}}{\text{Total Assets}}",
        'debt_to_income_ratio': r"\text{Debt to Income Ratio} = \frac{\text{Total Debt Payments}}{\text{Gross Income}}",
        'non_mortgage_debt_service_ratio': r"\text{Non-Mortgage Debt Service Ratio} = \frac{\text{Total Debt Payments} - \text{Mortgage Payment}}{\text{Gross Income}}",
        'household_debt_service_ratio': r"\text{Household Debt Service Ratio} = \frac{\text{Total Debt Payments} - \text{Mortgage Payment}}{\text{After-Tax Income}}",
        'liquid_savings_to_net_worth_ratio': r"\text{Liquid Savings to Net Worth Ratio} = \frac{\text{Cash Savings}}{\text{Net Worth}}",
        'invested_assets_to_net_worth_ratio': r"\text{Invested Assets to Net Worth Ratio} = \frac{\text{Invested Assets}}{\text{Net Worth}}",
        'solvency_ratio': r"\text{Solvency Ratio} = \frac{\text{Net Worth}}{\text{Total Assets}}",
        'basic_housing_ratio': r"\text{Basic Housing Ratio} = \frac{\text{Housing Costs}}{\text{Gross Income}}",
        'investment_assets_to_gross_pay_ratio': r"\text{Investment Assets to Gross Pay Ratio} = \frac{\text{Invested Assets} + \text{Cash}}{\text{Gross Income}}"
    }

def get_all_ratios():
    # Flat list of all ratios (in order)
    return [
        'liquidity_ratio',
        'after_tax_savings_ratio',
        'total_savings_ratio',
        'current_ratio',
        'debt_to_asset_ratio',
        'debt_to_income_ratio',
        'non_mortgage_debt_service_ratio',
        'household_debt_service_ratio',
        'liquid_savings_to_net_worth_ratio',
        'invested_assets_to_net_worth_ratio',
        'solvency_ratio',
        'basic_housing_ratio',
        'investment_assets_to_gross_pay_ratio'
    ]

############
# RUN PAGE #
############

st.session_state['plan'] = st.session_state['plan']

if 'display_person' not in st.session_state.keys():
    st.session_state['display_person'] = st.session_state['plan'].people[0].id

# Sidebar
utils.ui_functions.make_sidebar()

# Main Panel
st.header('Ratio Analysis')
utils.ui_functions.add_colorful_divider()

tabs = st.tabs([f'{TAB_RATIOS} Ratios'])

with tabs[0]:
    st.subheader('Financial Ratios')
    all_ratios = get_all_ratios()
    ratio_definitions = get_ratio_definitions()
    ratio_latex = get_ratio_latex()
    ratio_names = [utils.plotting.ratio_rec_dict.get(r, {}).get('name', r) for r in all_ratios]
    ratio_map = dict(zip(ratio_names, all_ratios))

    st.selectbox('Person',
                 [person.id for person in st.session_state['plan'].people if person.dependent==False]+['Joint'],
                 on_change=update_display_person,
                 format_func=format_name,
                 args=['ratios_display_person'],
                 key='ratios_display_person')
    ratio_name = st.selectbox('Ratio', ratio_names, key='single_ratio')
    ratio_key = ratio_map[ratio_name]

    # Compute ratios
    ratios_df = utils.plotting.compute_analytical_timeseries(st.session_state['plan'], st.session_state['display_person'])
    # Plot only the selected ratio
    st.plotly_chart(utils.plotting.ratio_plot(ratios_df, [ratio_key]), use_container_width=True)

    # Show the formula in LaTeX and the description below the plot
    st.latex(ratio_latex.get(ratio_key, ''))
    st.markdown(ratio_definitions.get(ratio_key, ''))