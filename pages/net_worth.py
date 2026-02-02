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

def update_display_year(key):
    st.session_state['display_year'] = st.session_state[key]

def update_display_person(key):
    st.session_state['display_person'] = st.session_state[key]

def format_name(person_id):
    if person_id == 'Joint':
        return('Joint')
    else:
        return(st.session_state['plan'].get_object_from_id(person_id).name)

def format_radio(num):
    if num == 1:
        return('Target = Age * Gross Income / 10')
    elif num == 2:
        return('Target = 10 * (Age/Retirement Age) * Gross Income')

############
# RUN PAGE #
############

st.session_state['plan'] = st.session_state['plan']

# Set up default values for each tab's person/year keys
if 'balance_display_person' not in st.session_state:
    st.session_state['balance_display_person'] = st.session_state['plan'].people[0].id
if 'balance_display_year' not in st.session_state:
    st.session_state['balance_display_year'] = st.session_state['plan'].start_year
if 'net_worth_display_person' not in st.session_state:
    st.session_state['net_worth_display_person'] = st.session_state['plan'].people[0].id
if 'retirement_display_person' not in st.session_state:
    st.session_state['retirement_display_person'] = st.session_state['plan'].people[0].id
if 'net_worth_level' not in st.session_state:
    st.session_state['net_worth_level'] = 'subcategory'
if 'retirement_level' not in st.session_state:
    st.session_state['retirement_level'] = 'subcategory'
if 'net_worth_radio' not in st.session_state:
    st.session_state['net_worth_radio'] = 2
if 'net_worth_include_pension' not in st.session_state:
    st.session_state['net_worth_include_pension'] = False
if 'retirement_include_pension' not in st.session_state:
    st.session_state['retirement_include_pension'] = False

# Sidebar
utils.ui_functions.make_sidebar()

# Main Panel
st.header('Net Worth')
utils.ui_functions.add_colorful_divider()

balance_sheet_tab, net_worth_tab, retirement_tab = st.tabs([f'{TAB_BALANCE_SHEET} Balance Sheet',f'{TAB_NET_WORTH} Net Worth',f'{TAB_RETIREMENT} Retirement'])

with balance_sheet_tab:
    st.subheader('Balance Sheet')
    c1, c2 = st.columns([0.5,0.5])
    with c1:
        st.selectbox('Year',st.session_state['plan'].cal_year,
                     on_change=update_display_year,
                     args=['balance_display_year'],
                     key='balance_display_year')
    with c2:
        st.selectbox('Person',
                     [person.id for person in st.session_state['plan'].people if person.dependent==False]+['Joint'],
                     on_change=update_display_person,
                     format_func=format_name,
                     args=['balance_display_person'],
                     key='balance_display_person')
    
    col1, col2 = st.columns([0.55,0.45])
    with col1:
        budget = utils.plotting.generate_statement(st.session_state['plan'],
                                                   st.session_state['balance_display_person'],
                                                   st.session_state['balance_display_year'],
                                                   statement_type='balance_sheet')
        
        st.dataframe(budget,hide_index=True,use_container_width=True)
    with col2:
        st.plotly_chart(st.session_state['plan'].pie_chart('assets',st.session_state['balance_display_year'],'pie'))

with net_worth_tab:
    st.subheader('Net Worth Projection')
    col1, col2 = st.columns([0.5,0.5])
    with col1:
        st.selectbox('Person',
                     [person.id for person in st.session_state['plan'].people if person.dependent==False]+['Joint'],
                     on_change=update_display_person,
                     format_func=format_name,
                     args=['net_worth_display_person'],
                     key='net_worth_display_person')
    with col2:
        st.selectbox('Display Aggregation Level',['category','subcategory','name'],key='net_worth_level')
        st.radio('Net Worth Target Formula',
                 options=[1,2],
                 format_func=format_radio,
                 key='net_worth_radio')
        st.checkbox('Include Pension Equivalent',
                    key='net_worth_include_pension')
    
    asset_plots_result = st.session_state['plan'].asset_plots(st.session_state['net_worth_display_person'],
                                                           st.session_state['net_worth_level'],
                                                           net_worth_formula=st.session_state['net_worth_radio'],
                                                           include_pension_equivalent=st.session_state['net_worth_include_pension'])
    
    st.plotly_chart(asset_plots_result['fig1'],
                    theme=None)

with retirement_tab:
    st.subheader('Retirement Projection')
    col1, col2 = st.columns([0.5,0.5])
    with col1:
        st.selectbox('Person',
                     [person.id for person in st.session_state['plan'].people if person.dependent==False]+['Joint'],
                     on_change=update_display_person,
                     format_func=format_name,
                     args=['retirement_display_person'],
                     key='retirement_display_person')
    with col2:
        st.selectbox('Display Aggregation Level',['category','subcategory','name'],key='retirement_level')
        st.checkbox('Include Pension Equivalent',
                    key='retirement_include_pension')
    
    retirement_plots_result = st.session_state['plan'].asset_plots(st.session_state['retirement_display_person'],
                                                           st.session_state['retirement_level'],
                                                           include_pension_equivalent=st.session_state['retirement_include_pension'])
    
    st.plotly_chart(retirement_plots_result['fig2'],
                    theme=None)