import streamlit as st 

import pandas as pd
import plotly.express as px

import objs.plan 
import objs.financial_objects
import utils.utilities
import utils.ui_functions
from utils.emoji_config import *

# Setup page configuration and CSS
utils.ui_functions.setup_page()

# To Do:

def add_liability_to_plan():
    utils.ui_functions.sidebar_buttons(False)

    if st.session_state['subcategory_new'] in ['Line of Credit','HELOC','Credit Card']:
        category = 'Revolving'
    elif st.session_state['subcategory_new'] in ['Mortgage','Student Loan','Auto Loan','Personal Loan','Medical Debt']:
        category = 'Installment'

            
    liability_obj = objs.financial_objects.LiabObj(st.session_state['plan'].get_object_from_name('Person',st.session_state['person_new']).id,category,st.session_state['subcategory_new'],st.session_state['name_new'],st.session_state['tax_keyword_new'],
                        st.session_state['plan'].cal_year,st.session_state['interest_rate_new'],st.session_state['value_new'],
                        True,True,attributes={'payment':st.session_state['payment_new']})
    
    st.session_state['plan'].liabilities.append(liability_obj)
    st.session_state['plan'] = liability_obj.project(st.session_state['plan'])

    st.session_state['plan'] = liability_obj.make_expense_obj(st.session_state['plan'])


@st.dialog('New Liability')    
def add_liability():
   if len([person for person in st.session_state['plan'].people if person.dependent == False]) > 1:
       joint = ['Joint']
   else:
       joint = []
   with st.form("new_liability"):
       # st.text("New Liability")
       st.selectbox("Subcategory",
                    options=['','Mortgage','Student Loan','Auto Loan','Personal Loan','Medical Debt'],
                    key='subcategory_new')
       st.text_input("Name",
                     key='name_new')
       st.selectbox("Person",
                    options=([person.name for person in st.session_state['plan'].people if person.dependent == False]+joint),
                    key='person_new')
       st.selectbox("Tax Keyword",
                    options=['','Student Loan','Medical Expenses'],
                    key='tax_keyword_new')
       st.number_input('Annual Interest Rate',
                       min_value=0.0,
                       max_value=1.0,
                       value=0.0,
                       step=0.001,
                       format="%0.3g",
                       key='interest_rate_new')
       st.number_input('Present Value',
                       min_value=0,
                       max_value=int(1e12),
                       value=0,
                       step=1,
                       key='value_new')
       st.number_input('Monthly Payment',
                       min_value=0.0,
                       max_value=1e12,
                       value=0.0,
                       step=0.01,
                       key='payment_new')
           
       # Add Close/Discard Button! 
       submit = st.form_submit_button(label="Add Liability to Plan",
                             on_click=add_liability_to_plan)
       if submit:
           st.rerun()

def remove_liability(liability_id):
    utils.ui_functions.sidebar_buttons(False)

    st.session_state["plan"].remove_object_by_id(liability_id)

def update_liability(liability_id,obj,attr):
    utils.ui_functions.sidebar_buttons(False)

    if attr == 'extra_payment':
        for ind in st.session_state[f"{liability_id}_"+attr]['edited_rows']:
            obj.extra_payment[obj.extra_payment.index[ind]] = st.session_state[f"{liability_id}_"+attr]['edited_rows'][ind]['extra_payment']
    else:
        setattr(obj,attr,st.session_state[f"{liability_id}_"+attr])
    
    st.session_state['plan'] = obj.project(st.session_state['plan'])
    
    #obj = obj.annualize_amort()
    #st.session_state['plan'] = obj.expense_obj(st.session_state['plan'])

def generate_static_liability(liability_id):    
    obj = st.session_state['plan'].get_object_from_id(liability_id)
    with st.container(border=True):
        st.write(obj.name+' ('+obj.person +') - '+str(int(obj.value[obj.start_year])))
    return(obj)

def generate_liability(liability_id):    
    obj = st.session_state['plan'].get_object_from_id(liability_id)
    if obj.person == 'Joint':
        person_name = 'Joint'
    else:
        person_name = st.session_state['plan'].get_object_from_id(obj.person).name
    with st.expander(label=(obj.name+' ('+person_name +') - '+str(int(obj.value[obj.start_year])))):

        st.write("Person",person_name)
        st.selectbox("Subcategory",
                     on_change=update_liability,
                     args=[liability_id,obj,'subcategory'],
                     options=[obj.subcategory]+[subcat for subcat in ['Retirement','Savings','Bonds','Automobile','Real Estate'] if subcat != obj.subcategory],
                     key=f'{liability_id}_subcategory')
        if st.session_state[f'{liability_id}_subcategory'] in ['Line of Credit','HELOC','Credit Card']:
            obj.category = 'Revolving'
        elif st.session_state[f'{liability_id}_subcategory'] in ['Mortgage','Student Loan','Auto Loan','Personal Loan','Medical Debt']:
            obj.category = 'Installment'
        st.selectbox("Tax Keyword",
                     options=[obj.tax_keyword]+[key for key in ['','Student Loan','Medical Expenses'] if key != obj.tax_keyword],
                     on_change=update_liability,args=[liability_id,obj,'tax_keyword'],
                     key=f'{liability_id}_tax_keyword')
        st.text_input("Name",
                      value=obj.name,
                      on_change=update_liability,
                      args=[liability_id,obj,'name'],
                      key=f'{liability_id}_name')
        st.number_input('Interest Rate',
                        min_value=0.0,
                        max_value=1.0,
                        value=obj.interest_rate,
                        step=0.001,
                        format="%0.3g",
                        on_change=update_liability,
                        args=[liability_id,obj,'interest_rate'],
                        key=f'{liability_id}_interest_rate')
        st.number_input('Present Value',
                        min_value=0,
                        max_value=int(1e12),
                        value=int(obj.value[obj.start_year]),
                        step=1,
                        on_change=update_liability,
                        args=[liability_id,obj,'value'],
                        key=f'{liability_id}_value')
        st.number_input('Monthly Payment',
                        min_value=0,
                        max_value=int(1e12),
                        value=int(obj.payment_annual[obj.start_year]/12),
                        step=1,
                        on_change=update_liability,
                        args=[liability_id,obj,'payment'],
                        key=f'{liability_id}_payment')
        st.write('Term (Months): '+str(obj.term))
        st.checkbox('Edit Extra Payments',key=f'{liability_id}_edit_extra')
        if st.session_state[f'{liability_id}_edit_extra'] == True:
            st.data_editor(obj.extra_payment.set_axis(obj.amortization_table['month'].astype(str)+'/'+obj.amortization_table['year'].astype(str)),
                           num_rows='fixed',
                           on_change=update_liability,
                           args=[liability_id,obj,'extra_payment'],
                           key=f'{liability_id}_extra_payment')
        st.button(f"{BUTTON_DELETE} Delete",
                  on_click=remove_liability,
                  args=[liability_id],key=f"{liability_id}_del")
        return(obj)


############
# RUN PAGE #
############

st.session_state['plan'] = st.session_state['plan']

# SIDEBAR
# with st.sidebar:
#     if 'plan' in st.session_state:
#         save_button = st.button("Save Plan",on_click=utils.ui_functions.save_plan,key='save')

utils.ui_functions.make_sidebar()

st.header('Liabilities')
utils.ui_functions.add_colorful_divider()

col1, col2 = st.columns(2)

with col1:
    col11,col12 = st.columns(2)
    with col11:
        st.button(f"{BUTTON_ADD_LIABILITY} New Liability",
                  use_container_width=True,
                  on_click=add_liability)
    #with col12:

    # Loop over each subcategory
    for cat in ['Revolving','Installment']:
        temp_obj_list = [obj for obj in st.session_state['plan'].liabilities if obj.category == cat and not obj.future_event]
        if len(temp_obj_list) > 0:
            st.subheader(cat+' Debt')
            for liability in sorted(temp_obj_list,key = lambda x: x.value[x.start_year], reverse=True):    
                liability_obj = st.session_state['plan'].get_object_from_id(liability.id)
                if liability_obj.editable == True:
                    liability_obj = generate_liability(liability.id)
                else:
                    liability_obj = generate_static_liability(liability.id)
         
with col2:
    st.write('Total Liabilities (',st.session_state['plan'].start_year,'): ',sum([obj.value[obj.start_year] for obj in st.session_state['plan'].liabilities if not obj.future_event]))
    st.plotly_chart(st.session_state['plan'].pie_chart('liabilities',st.session_state['plan'].start_year,'pie'))

