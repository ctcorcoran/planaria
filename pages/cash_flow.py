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

############
# RUN PAGE #
############

st.session_state['plan'] = st.session_state['plan']

# Set up default values for each tab's person/year keys
if 'budget_display_person' not in st.session_state:
    st.session_state['budget_display_person'] = st.session_state['plan'].people[0].id
if 'budget_display_year' not in st.session_state:
    st.session_state['budget_display_year'] = st.session_state['plan'].start_year
if 'sankey_display_person' not in st.session_state:
    st.session_state['sankey_display_person'] = st.session_state['plan'].people[0].id
if 'sankey_display_year' not in st.session_state:
    st.session_state['sankey_display_year'] = st.session_state['plan'].start_year
if 'projection_display_person' not in st.session_state:
    st.session_state['projection_display_person'] = st.session_state['plan'].people[0].id
if 'projection_after_tax' not in st.session_state:
    st.session_state['projection_after_tax'] = False
if 'sankey_comb' not in st.session_state:
    st.session_state['sankey_comb'] = False
if 'sankey_norm' not in st.session_state:
    st.session_state['sankey_norm'] = False

# Sidebar
utils.ui_functions.make_sidebar()

# Main Panel
st.header('Cash Flow')
utils.ui_functions.add_colorful_divider()

budget_tab, sankey_tab, projection_tab = st.tabs([f'{TAB_ANNUAL_BUDGET} Annual Budget',f'{TAB_CASH_FLOW_DIAGRAM} Cash Flow Diagram',f'{TAB_EXPENSE_PROJECTIONS} Expense Projections'])

with budget_tab:
    st.subheader('Annual Budget')
    c1, c2 = st.columns([0.5,0.5])
    with c1:
        st.selectbox('Year',st.session_state['plan'].cal_year,
                     on_change=update_display_year,
                     args=['budget_display_year'],
                     key='budget_display_year')
    with c2:
        st.selectbox('Person',
                     [person.id for person in st.session_state['plan'].people if person.dependent==False]+['Joint'],
                     on_change=update_display_person,
                     format_func=format_name,
                     args=['budget_display_person'],
                     key='budget_display_person')
    col1, col2 = st.columns([0.55,0.45])
    with col1:
        budget = utils.plotting.generate_statement(st.session_state['plan'],
                                                   st.session_state['budget_display_person'],
                                                   st.session_state['budget_display_year'],
                                                   statement_type='cashflow')
        st.dataframe(budget,hide_index=True,use_container_width=True)
    with col2:
        st.plotly_chart(st.session_state['plan'].pie_chart('expenses',
                                                          st.session_state['budget_display_year'],
                                                          'sunburst',
                                                          person=st.session_state['budget_display_person']))

with sankey_tab:
    st.subheader('Cash Flow Sankey Diagram')
    col1, col2, col3 = st.columns([0.33,0.33,0.33])
    with col1:
        st.selectbox('Year',st.session_state['plan'].cal_year,
                     on_change=update_display_year,
                     args=['sankey_display_year'],
                     key='sankey_display_year')
    with col2:
        st.selectbox('Person',
                     [person.id for person in st.session_state['plan'].people if person.dependent==False]+['Joint'],
                     on_change=update_display_person,
                     format_func=format_name,
                     args=['sankey_display_person'],
                     key='sankey_display_person')
    with col3:
        st.checkbox('Combine All Expenses',key='sankey_comb')
        st.checkbox('Display Values As Percentage',key='sankey_norm')
    st.plotly_chart(st.session_state['plan'].cashflow_sankey(st.session_state['sankey_display_person'],
                                                             st.session_state['sankey_display_year'],
                                                             st.session_state['sankey_comb'],
                                                             st.session_state['sankey_norm']))

with projection_tab:
    st.subheader('Expense Projections')
    col1, col2 = st.columns([0.5,0.5])
    with col1:
        st.selectbox('Person',
                     [person.id for person in st.session_state['plan'].people if person.dependent==False]+['Joint'],
                     on_change=update_display_person,
                     format_func=format_name,
                     args=['projection_display_person'],
                     key='projection_display_person')
    with col2:
        st.selectbox('Display Aggregation Level',['category','subcategory','name'],index=1,key='projection_level')
        st.checkbox('Display Normalized After-Tax Values',key='projection_after_tax')
    st.plotly_chart(st.session_state['plan'].expense_plots(st.session_state['projection_display_person'],
                                                           st.session_state['projection_level'],
                                                           st.session_state['projection_after_tax'])['fig'])