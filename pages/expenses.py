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

# Initialize session state for display toggles
if 'expense_display' not in st.session_state:
    st.session_state['expense_display'] = utils.ui_functions.get_config_value('ui_defaults', 'expense_display_default', 'Annual')

def add_expense_to_plan(keyword):
    utils.ui_functions.sidebar_buttons(False)

    attributes = {'infl_rate':st.session_state['plan'].col_rate}
    if st.session_state['ann_month_new'] == 'Annual':
        multi = 1 
    elif st.session_state['ann_month_new'] == 'Monthly':
        multi = 12
    value = st.session_state['value_new']*multi
    
    if keyword == 'Discretionary':
        subcat = 'Discretionary'
        tax_keyword = ''
    else:
        subcat = st.session_state['subcategory_new']
        tax_keyword = st.session_state['tax_keyword_new']
        
    if st.session_state['person_new'] == 'Joint':
        person = 'Joint'
    else:
        person = st.session_state['plan'].get_object_from_name('Person',st.session_state['person_new']).id
            
    exp_obj = objs.financial_objects.ExpenseObj(person,
                                                keyword,
                                                subcat,
                                                st.session_state['name_new'],
                                                tax_keyword,
                                                st.session_state['plan'].cal_year,value,
                                                st.session_state['fixed_new'],
                                                True,
                                                attributes)
    
    st.session_state['plan'].expenses.append(exp_obj)
    st.session_state['plan'] = exp_obj.project(st.session_state['plan'])
 
@st.dialog('New Expense')    
def add_expense(keyword):
    if len([person for person in st.session_state['plan'].people if person.dependent == False]) > 1:
        joint = ['Joint']
    else:
        joint = []
    with st.form("new_expense"):
        # st.text("New Expense")
        st.text_input("Name",
                      key='name_new')
        st.write("Category: ",keyword)
        #st.selectbox("Category",options=['Necessary','Discretionary'],key='category_new')
        if keyword == 'Necessary':
            st.selectbox("Subcategory",
                         options=['Home','Car/Transportation','Family','Other'],
                         key='subcategory_new')
        #
        st.selectbox("Person",
                     options=([person.name for person in st.session_state['plan'].people if person.dependent == False]+joint),
                     key='person_new')
        if keyword == 'Necessary':
            st.selectbox("Tax Keyword",
                         options=['','Medical','Charitable Donations','Health Insurance'],
                         key='tax_keyword_new')
        #
        st.checkbox("Fixed",key='fixed_new') 
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Value",min_value=0,key='value_new')
        with col2:
            st.radio(label='AnnMonth',
                     options=['Annual','Monthly'],
                     index=['Annual','Monthly'].index(st.session_state['expense_display']),
                     key='ann_month_new',
                     label_visibility='hidden')
        # Add Close/Discard Button! 
        submit = st.form_submit_button(label="Add Expense to Plan",
                              on_click=add_expense_to_plan,
                              args=[keyword])
        if submit:
            st.rerun()

# Start Here

def remove_expense(expense_id):
    utils.ui_functions.sidebar_buttons(False)

    st.session_state["plan"].remove_object_by_id(expense_id)

def update_expense(expense_id,obj,attr):
    utils.ui_functions.sidebar_buttons(False)

    if attr == 'value':
        if (f'{expense_id}_ann_month' in st.session_state) & (st.session_state[f'{expense_id}_ann_month'] == 'Monthly'):
            multi = 12
        else:
            multi = 1
        raw_value = st.session_state.get(f"{expense_id}_"+attr)
        if isinstance(raw_value, pd.Series):
            value_series = raw_value.copy()
            value_series.index = value_series.index.astype(int)
        elif isinstance(raw_value, pd.DataFrame):
            if raw_value.shape[1] == 1:
                value_series = raw_value.iloc[:, 0]
            else:
                value_series = pd.Series(raw_value.squeeze())
            value_series.index = value_series.index.astype(int)
        else:
            value_series = pd.Series([raw_value for _ in st.session_state['plan'].cal_year],
                                     index=st.session_state['plan'].cal_year)
        if obj.fixed:
            setattr(obj, attr, multi * value_series)
        else:
            obj.value_input = multi * value_series

    else:
        setattr(obj,attr,st.session_state[f"{expense_id}_"+attr])
        
    st.session_state['plan'] = obj.project(st.session_state['plan'])

def generate_static_expense(expense_id,disp_div):    
    obj = st.session_state['plan'].get_object_from_id(expense_id)
    with st.container(border=True):
        st.write(obj.name+' ('+st.session_state['plan'].get_object_from_id(obj.person).name +') - '+str(int(obj.value[obj.start_year]/disp_div)))
    return(obj)

def generate_expense(expense_id,disp_div):    
    obj = st.session_state['plan'].get_object_from_id(expense_id)
    if obj.person == 'Joint':
        person_name = 'Joint'
    else:
        person_name = st.session_state['plan'].get_object_from_id(obj.person).name
    with st.expander(label=(obj.name+' ('+ person_name +') - '+str(int(obj.value[obj.start_year]/disp_div)))):
        # Allow for "Joint" person if there are two (or more) non-dependents
        # if len([person for person in st.session_state['plan'].people if person.dependent == False]) > 1:
        #     joint = ['Joint']
        # else:
        #     joint = []
        st.write("Person: ",person_name)
        st.write("Category: ",obj.category)
        if obj.category == 'Necessary':
            st.selectbox("Subcategory",
                         on_change=update_expense,
                         args=[expense_id,obj,'subcategory'],
                         options=[obj.subcategory]+[subcat for subcat in ['Home','Utilities','Car/Transportation','Family'] if subcat != obj.subcategory],
                         key=f'{expense_id}_subcategory')
        st.text_input("Name",
                      value=obj.name,on_change=update_expense,
                      args=[expense_id,obj,'name'],
                      key=f'{expense_id}_name')
        st.selectbox("Tax Keyword",
                     options=[obj.tax_keyword]+[key for key in ['','Medical','Charitable Donations','Health Insurance'] if key != obj.tax_keyword],
                     on_change=update_expense,args=[expense_id,obj,'tax_keyword'],
                     key=f'{expense_id}_tax_keyword')
        st.checkbox("Fixed",
                    value=obj.fixed,on_change=update_expense,
                    args=[expense_id,obj,'fixed'],
                    key=f'{expense_id}_fixed')
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox(label='Value Entry',
                         options=['Auto','Manual'],
                         key=f'{expense_id}_val_entry')
        with col2:
            st.radio(label='AnnMonth',
                     options=['Annual','Monthly'],
                     index=1,
                     key=f'{expense_id}_ann_month',
                     label_visibility='hidden')
            if st.session_state[f'{expense_id}_ann_month'] == 'Annual':
                multi = 1 
            elif st.session_state[f'{expense_id}_ann_month'] == 'Monthly':
                multi = 12
        if st.session_state[f'{expense_id}_val_entry'] == 'Auto':
            st.number_input("Value",
                            min_value=0,
                            max_value=int(1e12),
                            value=int(obj.value[obj.start_year]/multi),
                            step=1,
                            on_change=update_expense,
                            args=[expense_id,obj,'value'],
                            key=f'{expense_id}_value')
        else:
            st.write(f'Enter values in {obj.start_year} dollars')
            obj.value = st.data_editor(obj.deflate().value.set_axis(obj.value.index.astype(str))/multi,
                                       num_rows='fixed',
                                       on_change=update_expense,
                                       args=[expense_id,obj,'value'],
                                       key=f'{expense_id}_value').set_axis(obj.value.index)
        
        st.button(f"{BUTTON_DELETE} Delete",
                  on_click=remove_expense,
                  args=[expense_id],
                  key=f"{expense_id}_del")
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


st.header('Expenses')
utils.ui_functions.add_colorful_divider()

col1, col2 = st.columns(2)

with col1:

    if st.session_state['expense_display'] == 'Monthly':
        disp_div = 12
    elif st.session_state['expense_display'] == 'Annual':
        disp_div = 1
    # st.button("New Expense (Value)",on_click=add_expense)
    
    col11,col12 = st.columns(2)
    with col11:
        st.button(f"{BUTTON_ADD_NECESSARY_EXPENSE} New Necessary Expense",
                  use_container_width=True,
                  on_click=add_expense,
                  args=['Necessary'])
    with col12:
        st.button(f"{BUTTON_ADD_DISCRETIONARY_EXPENSE} New Discretionary Expense",
                  use_container_width=True,
                  on_click=add_expense,
                  args=['Discretionary'])
    
    # Loop over each category 

    for cat in ['Necessary','Discretionary','Savings']:
        # Get objects that have a nonzero value for the plan start year
        temp_obj_list = [obj for obj in st.session_state['plan'].expenses if obj.category == cat and obj.value[st.session_state['plan'].start_year]>0 and not obj.future_event]
        if len(temp_obj_list) > 0:
            st.subheader(cat)
            # Sort by value in the plan start year
            for obj in sorted(temp_obj_list,key = lambda x: x.value[st.session_state['plan'].start_year], reverse=True): #x.value[x.start_year], reverse=True):    
                obj = st.session_state['plan'].get_object_from_id(obj.id)
                if obj.editable == True:
                    obj = generate_expense(obj.id,disp_div)
                else:
                    if obj.value[obj.start_year] > 0:
                        obj = generate_static_expense(obj.id,disp_div)    
         
with col2:
    st.write('Total Expenses (',st.session_state['plan'].start_year,'): ',sum([obj.value[obj.start_year] for obj in st.session_state['plan'].expenses if not obj.future_event]))
    st.plotly_chart(st.session_state['plan'].pie_chart('expenses',st.session_state['plan'].start_year,'sunburst',cats_to_ignore=['Tax']))

# Display Value toggle at bottom
st.selectbox('Display Value',
             options=['Monthly','Annual'],
             key='expense_display')

