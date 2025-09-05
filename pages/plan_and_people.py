#https://medium.com/streamlit/creating-repeatable-items-in-streamlit-cb8b6264e1e6

import streamlit as st 
import pandas as pd

import objs.plan 
import utils.utilities
import utils.ui_functions
from utils.emoji_config import *

# Setup page configuration and CSS
utils.ui_functions.setup_page()

# NEED TO MAKE UPDATE PLAN MORE ROBUST, ESPECIALLY YEARS
# Make sure that if Start Year increases, Marriage Year does too...

def update_plan(attr):
    utils.ui_functions.sidebar_buttons(False)
    
    setattr(st.session_state['plan'],attr,st.session_state['plan_'+attr])
    if attr in ['start_year','n_years']:
        st.session_state['plan'].cal_year = pd.Series([st.session_state['plan'].start_year + i for i in range(st.session_state['plan'].n_years+1)])
        # Push cal_year down to other objects

# MARRIAGE AND EXPENSE SHARE

def update_marriage():
    utils.ui_functions.sidebar_buttons(False)
    
    # If already married, marriage_year=start_year is equivalent to marriage_year < start_year
    if st.session_state['plan_married'] == True:
        st.session_state['plan'].marriage_year = st.session_state['plan_start_year']
    else:
        if 'plan_marriage_year' in st.session_state:
            st.session_state['plan'].marriage_year = st.session_state['plan_marriage_year']
    st.session_state['plan'].get_married(st.session_state['plan'].marriage_year)
  
def update_combine(expense_list):
    utils.ui_functions.sidebar_buttons(False)
    
    if st.session_state['plan_married'] == True:
        st.session_state['plan'].get_married(st.session_state['plan_start_year'])
    else:
        st.session_state['plan'].get_married(st.session_state['plan_marriage_year'])
        
    st.session_state['plan'].combine_expenses(expense_list,st.session_state['plan_combine_year'])
    
def update_expense_share():
    utils.ui_functions.sidebar_buttons(False)
    
    st.session_state['plan'].expense_share = st.session_state['plan_expense_share']
    st.session_state['plan'].generate_expense_share()    

# PERSON Functions

def add_person_to_plan():
    utils.ui_functions.sidebar_buttons(False)
    
    new_person = objs.plan.Person(
        st.session_state['name_new'],
        st.session_state['plan'].start_year-st.session_state['current_age_new'],
        st.session_state['plan'].cal_year,
        st.session_state['dependent_new'])
    st.session_state["plan"].people.append(new_person)
    st.session_state['plan'].drawdown_order[new_person.id] = []

@st.dialog('New Person')  
def add_person():
    #After two non-dependents, only allow dependents
    if len([obj for obj in st.session_state['plan'].people if obj.dependent == False]) == 2:
        dep = True
        dis = True
    else:
        dep = False
        dis = False
    with st.form("new_person"):
        st.text_input("Name",key="name_new")
        st.number_input("Age",value=0,min_value=0,max_value=100,step=1,key="current_age_new")
        st.checkbox("Dependent",value=dep,disabled=dis,key="dependent_new") 
        submit = st.form_submit_button(label="Add Person to Plan",
                              on_click=add_person_to_plan)
    if submit:
        st.rerun()

def remove_person(person_id):
    utils.ui_functions.sidebar_buttons(False)
    
    st.session_state["plan"].remove_object_by_id(person_id)

def update_person(person_id,obj,attr):
    utils.ui_functions.sidebar_buttons(False)
    
    if attr == 'current_age':
        setattr(obj,'birth_year',st.session_state['plan'].start_year-st.session_state[f"{person_id}_"+attr])
    else:   
        setattr(obj,attr,st.session_state[f"{person_id}_"+attr])
    #st.session_state['container_names'][person_id] = st.session_state[f"{person_id}_name"]

def generate_person(person_id):    
    obj = st.session_state['plan'].get_object_from_id(person_id)

    with st.expander(label=obj.name): 
        st.text_input("Name",value=obj.name,on_change=update_person,args=[person_id,obj,'name'],key= f"{person_id}_name")
        st.number_input("Age",value=obj.current_age,step=1,on_change=update_person,args=[person_id,obj,'current_age'],key=f"{person_id}_current_age")
        st.checkbox("Dependent",value=obj.dependent,on_change=update_person,args=[person_id,obj,'dependent'],key=f"{person_id}_dependent")
        st.button(f"{BUTTON_DELETE} Delete",on_click=remove_person,args=[person_id],key=f"{person_id}_del")
        return(obj)

# DRAWDOWN 

# def generate_drawdown_item(ind):
#     st.selectbox(st.session_state['plan'].drawdown_order[ind],
#                  options=[ind]+[i for i in range(1,len(st.session_state['plan'].drawdown_order)+1) if i != ind],
#                  on_change=update_drawdown,
#                  args=[ind],
#                  key=f'plan_drawdown_{ind}')

# def update_drawdown(ind):
#     name = st.session_state['plan'].drawdown_order.pop(ind)
#     st.session_state['plan'].drawdown_order.insert(st.session_state[f'plan_drawdown_{ind}']-1,name)


############
# RUN PAGE #
############

st.session_state['plan'] = st.session_state['plan']

# SIDEBAR
utils.ui_functions.make_sidebar()

st.header('Plan & People Settings')
utils.ui_functions.add_colorful_divider()

col1, col2 = st.columns(2)

# Will eventually need to address how to change all of these for the 
# plan, but I don't think object methods are the way to go...we'll see

with col1:
    st.write('Plan')
    st.text_input("Plan Name",
                  value=st.session_state['plan'].name,
                  on_change=update_plan,
                  args=['name'],key="plan_name")
    st.number_input("Start Year",
                  min_value=2024,
                  value=st.session_state['plan'].start_year,
                  step=1,
                  on_change=update_plan,
                  args=['start_year'],key="plan_start_year")
    st.number_input("Future Years",
                  min_value=0,
                  value=st.session_state['plan'].n_years,
                  step=1,
                  on_change=update_plan,
                  args=['n_years'],key="plan_n_years")
    st.number_input("Inflation Rate",
                  min_value=0.0,
                  max_value=1.0,
                  value=st.session_state['plan'].infl_rate,
                  step=0.005,
                  on_change=update_plan,
                  args=['infl_rate'],key="plan_infl_rate")
    st.number_input("COL Raise Rate",
                  min_value=0.0,
                  max_value=1.0,
                  value=st.session_state['plan'].infl_rate,
                  step=0.005,
                  on_change=update_plan,
                  args=['col_rate'],key="plan_col_rate")

    # with st.expander(label="Savings Drawdown Order: "):
    #     for i in range(len(st.session_state['plan'].drawdown_order)):
    #         generate_drawdown_item(i+1)

with col2:
    st.write('People')    
    # Only show adults (non-dependents)
    adults = [person for person in st.session_state['plan'].people if person.dependent == False]
    for person in adults:
        person_obj = st.session_state['plan'].get_object_from_id(person.id) 
        person_obj = generate_person(person.id)
    if len(adults) < 2:
        st.button(f"{BUTTON_ADD_PERSON} Add Person",on_click=add_person)
    st.info("Children are managed as current or future expenses and are not shown here.")
    if len(adults) == 2:
        # Marriage (placed above expense split per convention)
        st.checkbox('Married',
                    value=st.session_state['plan'].married[st.session_state['plan'].start_year],
                    on_change=update_marriage,
                    key='plan_married')
        # Expense Share
        st.selectbox('Joint Expense Share',
                     options=[st.session_state['plan'].expense_share]+[share for share in ['Even','Income-Based'] if share != st.session_state['plan'].expense_share],
                     on_change=update_expense_share,
                     #args=['expense_share'],
                     key='plan_expense_share')
        # If unchecked, the user controls the marriage event via Future Events page (button)
        
