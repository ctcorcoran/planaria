import streamlit as st
import copy
import json

import objs.plan 
import utils.utilities
import utils.ui_functions
import pandas as pd
import os

# Setup page configuration and CSS
utils.ui_functions.setup_page()

# https://github.com/streamlit/streamlit/issues/5813#issuecomment-1341310542

for key in ['plan','load_file']:
    if key not in st.session_state.keys():
        st.session_state[key] = None
            
st.session_state['plan'] = st.session_state['plan']  

@st.dialog('New Plan')
def new_plan():
    with st.form("new_plan"):
        st.text_input("Plan Name",key='plan_name')
        submit = st.form_submit_button(label="Create New Plan",
                              on_click=utils.ui_functions.set_new_plan)
    if submit:
        st.rerun()

@st.dialog('Load Plan')
def load_plan():
    load = st.file_uploader('Load Plan',key='load_file')
    if load:
        st.rerun()

# SIDEBAR
if st.session_state['plan'] is not None:
    utils.ui_functions.make_sidebar()

# MAIN

st.title('PLANARIA')

st.header('A Personal Financial Planning App')
utils.ui_functions.add_colorful_divider()

# BUTTONS
st.button('New Plan',on_click=new_plan,use_container_width=True)
st.button('Load Plan',on_click=load_plan,use_container_width=True)

# NEW

#LOAD

# PRE LOAD (TEMPORARY)
# load_test = 'saved_plans/Test.json'

# with open(load_test, 'r') as j:
#     st.session_state['plan'] = utils.utilities.json_to_plan(json.loads(j.read()))
 
# st.session_state['plan_updated'] = True
# st.session_state['plan_saved'] = True
# utils.ui_functions.make_sidebar()
    
# PERMANENT 

if st.session_state['load_file'] is not None:
    st.session_state['plan'] = copy.deepcopy(utils.utilities.json_to_plan(json.load(st.session_state['load_file'])))
    st.session_state['plan_updated'] = True
    st.session_state['plan_saved'] = True
    utils.ui_functions.make_sidebar()
