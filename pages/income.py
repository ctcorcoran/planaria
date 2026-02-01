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
if 'income_display' not in st.session_state:
    st.session_state['income_display'] = utils.ui_functions.get_config_value('ui_defaults', 'income_display_default', 'Annual')

def add_income_to_plan():
    utils.ui_functions.sidebar_buttons(False)

    if st.session_state['ann_month_new'] == 'Annual':
        multi = 1 
    elif st.session_state['ann_month_new'] == 'Monthly':
        multi = 12
    value = st.session_state['value_new']*multi
    if st.session_state['subcategory_new'] in ['Salary']:
        category = 'Earned'
    if st.session_state['fixed_new'] == False:
        attributes = {'infl_rate':st.session_state['plan'].col_rate}
    else:
        attributes = {}
        
    inc_obj = objs.financial_objects.IncomeObj(st.session_state['plan'].get_object_from_name('Person',st.session_state['person_new']).id,
                                               category,
                                               st.session_state['subcategory_new'],
                                               st.session_state['subcategory_new'],
                                               st.session_state['plan'].cal_year,value,
                                               st.session_state['fixed_new'],
                                               st.session_state['taxable_new'],
                                               True,
                                               attributes)
    
    st.session_state['plan'].income.append(inc_obj)
    st.session_state['plan'] = inc_obj.project(st.session_state['plan'])

def add_pension_to_income(income_id):
    """Add pension to an existing salary income."""
    utils.ui_functions.sidebar_buttons(False)
    
    income = st.session_state['plan'].get_object_from_id(income_id)
    if income is None or income.subcategory != 'Salary':
        st.error("Can only add pension to Salary income")
        return
    
    # Get pension parameters from session state
    contribution_rate = st.session_state.get(f'{income_id}_pension_contribution', 0.06)
    service_start_year = st.session_state.get(f'{income_id}_pension_service_start', st.session_state['plan'].start_year)
    vesting_years = st.session_state.get(f'{income_id}_pension_vesting', 5)
    final_avg_years = st.session_state.get(f'{income_id}_pension_final_avg', 3)
    retirement_age = st.session_state.get(f'{income_id}_pension_retirement', 65)
    
    # Add pension to the income (contribution_rate is already in decimal form)
    st.session_state['plan'] = income.make_pension_asset(
        st.session_state['plan'],
        contribution_rate=contribution_rate,
        service_start_year=service_start_year,
        vesting_years=vesting_years,
        final_avg_years=final_avg_years,
        retirement_age=retirement_age
    )
    
    st.success(f"Pension added to {income.name}")

def remove_pension_from_income(income_id):
    """Remove pension from an income."""
    utils.ui_functions.sidebar_buttons(False)
    
    income = st.session_state['plan'].get_object_from_id(income_id)
    if income is None:
        return
    
    st.session_state['plan'] = income.remove_pension(st.session_state['plan'])
    st.success(f"Pension removed from {income.name}")

def add_payroll_tax_to_income(income_id):
    """Add a payroll tax add-on to an existing salary income."""
    utils.ui_functions.sidebar_buttons(False)
    
    income = st.session_state['plan'].get_object_from_id(income_id)
    if income is None or income.subcategory != 'Salary':
        st.error("Can only add payroll tax to Salary income")
        return
    
    tax_name = st.session_state.get(f'{income_id}_payroll_tax_name', '').strip()
    tax_rate = st.session_state.get(f'{income_id}_payroll_tax_rate', 0.0)
    if tax_name == '':
        st.error("Payroll tax name is required")
        return
    
    income.add_payroll_tax(tax_name, tax_rate)
    st.session_state['plan'] = income.project(st.session_state['plan'])
    st.success(f"Payroll tax added to {income.name}")

def remove_payroll_tax_from_income(income_id, tax_index):
    """Remove a payroll tax add-on from an income."""
    utils.ui_functions.sidebar_buttons(False)
    
    income = st.session_state['plan'].get_object_from_id(income_id)
    if income is None:
        return
    
    income.remove_payroll_tax(tax_index)
    st.session_state['plan'] = income.project(st.session_state['plan'])
    st.success(f"Payroll tax removed from {income.name}")

def update_contribution_rate(income_id, obj):
    """Update only the contribution rate in the expense object."""
    utils.ui_functions.sidebar_buttons(False)
    
    # Get new contribution rate from session state
    new_contribution_rate = st.session_state.get(f'{income_id}_edit_contribution', 0.06)
    
    # Find the pension contribution expense and update its paired attributes
    for pair_list in st.session_state['plan'].pairs.values():
        for pair in pair_list:
            if pair[0] == income_id:
                child_obj = st.session_state['plan'].get_object_from_id(pair[1])
                if (child_obj is not None and 
                    child_obj.obj_type == 'Expense' and 
                    child_obj.name.startswith('Pension Contribution')):
                    # Update the contribution rate in the paired attributes
                    if income_id in child_obj.paired_attr['series']:
                        for attr_pair in child_obj.paired_attr['series'][income_id]:
                            if attr_pair[0] == 'value' and attr_pair[1] == 'value':
                                attr_pair[2] = new_contribution_rate
                    break
    
    # Reproject the parent income object to trigger expense update
    st.session_state['plan'] = obj.project(st.session_state['plan'])

def update_pension_parameters(income_id, obj):
    """Update pension parameters and reproject the income object."""
    utils.ui_functions.sidebar_buttons(False)
    
    # Get current values from session state
    service_start_year = st.session_state.get(f'{income_id}_edit_service_start', st.session_state['plan'].start_year)
    vesting_years = st.session_state.get(f'{income_id}_edit_vesting', 5)
    final_avg_years = st.session_state.get(f'{income_id}_edit_final_avg', 3)
    retirement_age = st.session_state.get(f'{income_id}_edit_retirement', 65)
    
    # Update the pension parameters
    obj.pension_params.update({
        'service_start_year': service_start_year,
        'vesting_years': vesting_years,
        'final_avg_years': final_avg_years,
        'retirement_age': retirement_age
    })
    
    # Reproject the income object to trigger cascading updates to child objects
    st.session_state['plan'] = obj.project(st.session_state['plan'])

@st.dialog('Add Pension')
def add_pension(income_id):
    """Dialog to configure and add pension to an income."""
    income = st.session_state['plan'].get_object_from_id(income_id)
    if income is None or income.subcategory != 'Salary':
        st.error("Can only add pension to Salary income")
        return
    
    with st.form(f"add_pension_{income_id}"):
        st.write(f"Adding pension to: {income.name}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Contribution Rate",
                           min_value=0.0, max_value=1.0, value=0.06, step=0.01,
                           key=f'{income_id}_pension_contribution',
                           help="Employee contribution rate (0.0 to 1.0)")
            st.number_input("Service Start Year",
                           min_value=1950, max_value=2100, value=st.session_state['plan'].start_year,
                           key=f'{income_id}_pension_service_start')
            st.number_input("Vesting Years",
                           min_value=0, max_value=20, value=5,
                           key=f'{income_id}_pension_vesting')
        with col2:
            st.number_input("Final Average Years",
                           min_value=1, max_value=10, value=3,
                           key=f'{income_id}_pension_final_avg')
            st.number_input("Retirement Age",
                           min_value=50, max_value=80, value=65,
                           key=f'{income_id}_pension_retirement')
        
        submit = st.form_submit_button("Add Pension", on_click=add_pension_to_income, args=[income_id])
        if submit:
            st.rerun()

@st.dialog('Add Payroll Tax')
def add_payroll_tax(income_id):
    """Dialog to configure and add a payroll tax add-on to an income."""
    income = st.session_state['plan'].get_object_from_id(income_id)
    if income is None or income.subcategory != 'Salary':
        st.error("Can only add payroll tax to Salary income")
        return
    
    with st.form(f"add_payroll_tax_{income_id}"):
        st.write(f"Adding payroll tax to: {income.name}")
        st.text_input("Payroll Tax Name",
                      value="Local Payroll Tax",
                      key=f'{income_id}_payroll_tax_name')
        st.number_input("Payroll Tax Rate (Proportion)",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.0,
                        step=0.01,
                        key=f'{income_id}_payroll_tax_rate',
                        help="Proportion of salary (0.0 to 1.0)")
        
        submit = st.form_submit_button("Add Payroll Tax", on_click=add_payroll_tax_to_income, args=[income_id])
        if submit:
            st.rerun()



@st.dialog('New Income')
def add_income(): 
   with st.form("new_income"):
        st.selectbox("Subcategory",
                     options=['Salary'],
                     key='subcategory_new')
        st.selectbox("Person",
                     options=[person.name for person in st.session_state['plan'].people if person.dependent == False],
                     key='person_new')
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Value",
                            min_value=0,
                            key='value_new')
        with col2:
            st.radio(label='AnnMonth',
                     options=['Annual','Monthly'],
                     key='ann_month_new',
                     label_visibility='hidden')
        st.checkbox("Fixed",
                    key='fixed_new')
        st.checkbox("Taxable",
                    value=True,
                    key='taxable_new')
        
        submit = st.form_submit_button(label="Add Income to Plan",
                                       on_click=add_income_to_plan)
        if submit:
            st.rerun()
            
def remove_income(income_id):
    utils.ui_functions.sidebar_buttons(False)

    st.session_state["plan"].remove_object_by_id(income_id)

def update_income(income_id,obj,attr):
    utils.ui_functions.sidebar_buttons(False)

    if attr == 'value':
        if (f'{income_id}_ann_month' in st.session_state) & (st.session_state[f'{income_id}_ann_month'] == 'Monthly'):
            multi = 12
        else:
            multi = 1
        raw_value = st.session_state.get(f"{income_id}_"+attr)
        base_series = obj.value_input if hasattr(obj, 'value_input') else obj.deflate().value
        base_series = base_series.reindex(st.session_state['plan'].cal_year)
        value_series = utils.utilities.data_editor_to_series(raw_value,
                                                             base_series,
                                                             list(st.session_state['plan'].cal_year))
        if obj.fixed:
            setattr(obj, attr, multi * value_series)
        else:
            obj.value_input = multi * value_series
        
    else:
        setattr(obj,attr,st.session_state[f"{income_id}_"+attr])
        
    st.session_state['plan'] = obj.project(st.session_state['plan'])

def generate_static_income(income_id,disp_div):    
    obj = st.session_state['plan'].get_object_from_id(income_id)
    with st.container(border=True):
        st.write(obj.name+' ('+obj.person +') - '+str(int(obj.value[obj.start_year]/disp_div)))
    return(obj)

def generate_income(income_id,disp_div):   
    obj = st.session_state['plan'].get_object_from_id(income_id)
    if obj.person == 'Joint':
        person_name = 'Joint'
    else:
        person_name = st.session_state['plan'].get_object_from_id(obj.person).name
    with st.expander(label=(obj.name+' ('+person_name +') - '+str(int(obj.value[obj.start_year]/disp_div)))):
        # Allow for "Joint" person if there are two (or more) non-dependents
        # if len([person for person in st.session_state['plan'].people if person.dependent == False]) > 1:
        #     joint = ['Joint']
        # else:
        #     joint = []
        st.write("Person: ",person_name)
        st.write("Subcategory: ",obj.subcategory)
        #
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox(label='Value Entry',
                         options=['Auto','Manual']
                         ,key=f'{income_id}_val_entry')
        with col2:
            st.radio(label='AnnMonth',
                     options=['Annual','Monthly'],
                     key=f'{income_id}_ann_month',
                     label_visibility='hidden')
            if st.session_state[f'{income_id}_ann_month'] == 'Annual':
                multi = 1 
            elif st.session_state[f'{income_id}_ann_month'] == 'Monthly':
                multi = 12
        if st.session_state[f'{income_id}_val_entry'] == 'Auto':
            st.number_input("Value",min_value=0,max_value=int(1e12),value=int(obj.value[obj.start_year]/multi),step=1,on_change=update_income,args=[income_id,obj,'value'],key=f'{income_id}_value')
        else:
            st.write(f'Enter values in {obj.start_year} dollars')
            base_series = obj.value_input if hasattr(obj, 'value_input') else obj.deflate().value
            base_series = base_series.reindex(st.session_state['plan'].cal_year)
            obj.value = st.data_editor(base_series.set_axis(base_series.index.astype(str))/multi,
                                       num_rows='fixed',
                                       on_change=update_income,
                                       args=[income_id,obj,'value'],
                                       key=f'{income_id}_value').set_axis(obj.value.index)
            
            #WHEN TO UPDATE, and KEEP UNINFLATED ENTRY WITH MANUAL
        
        st.checkbox("Fixed",value=obj.fixed,on_change=update_income,args=[income_id,obj,'fixed'],key=f'{income_id}_fixed')
        st.checkbox("Taxable",value=obj.taxable,on_change=update_income,args=[income_id,obj,'taxable'],key=f'{income_id}_taxable')

        # Pension controls - only show for Salary incomes
        if obj.subcategory == 'Salary':
            st.divider()
            st.write("**Pension Configuration**")
            
            # Recover pension_params if child pension objects exist
            if not hasattr(obj, 'pension_params'):
                child_ids = []
                for pair_list in st.session_state['plan'].pairs.values():
                    if not isinstance(pair_list, (list, tuple)):
                        continue
                    for pair in pair_list:
                        if isinstance(pair, (list, tuple)) and len(pair) > 1:
                            parent_id, child_id = pair[0], pair[1]
                        elif isinstance(pair, dict):
                            parent_id = pair.get('parent') or pair.get('source')
                            child_id = pair.get('child') or pair.get('target')
                        else:
                            continue
                        if parent_id == obj.id:
                            child_ids.append(child_id)
                pension_children = []
                for child_id in child_ids:
                    child_obj = st.session_state['plan'].get_object_from_id(child_id)
                    if child_obj is None:
                        continue
                    if (child_obj.obj_type == 'Expense' and child_obj.name.startswith('Pension Contribution')) or \
                       (child_obj.obj_type == 'Asset' and child_obj.name == 'Pension Equivalent'):
                        pension_children.append(child_id)
                if len(pension_children) > 0:
                    obj.pension_params = {
                        'service_start_year': st.session_state['plan'].start_year,
                        'vesting_years': 5,
                        'final_avg_years': 3,
                        'retirement_age': 65,
                    }
                    obj.dependent_objs = True
            
            if hasattr(obj, 'pension_params'):
                # Show pension parameters and allow editing
                st.write("✅ Pension Enabled")
                
                # Make pension parameters editable with automatic updates
                col1, col2 = st.columns(2)
                with col1:
                    contribution_rate = st.number_input("Contribution Rate",
                                                     min_value=0.0, max_value=1.0, 
                                                     value=obj.get_pension_contribution_rate(st.session_state['plan']) if obj.get_pension_contribution_rate(st.session_state['plan']) is not None else 0.06,
                                                     step=0.01,
                                                     key=f'{income_id}_edit_contribution',
                                                     help="Employee contribution rate (0.0 to 1.0)",
                                                     on_change=update_contribution_rate,
                                                     args=[income_id, obj])
                    service_start_year = st.number_input("Service Start Year",
                                                       min_value=1950, max_value=2100, 
                                                       value=obj.pension_params.get('service_start_year', st.session_state['plan'].start_year),
                                                       key=f'{income_id}_edit_service_start',
                                                       on_change=update_pension_parameters,
                                                       args=[income_id, obj])
                    vesting_years = st.number_input("Vesting Years",
                                                  min_value=0, max_value=20, 
                                                  value=obj.pension_params.get('vesting_years', 5),
                                                  key=f'{income_id}_edit_vesting',
                                                  on_change=update_pension_parameters,
                                                  args=[income_id, obj])
                with col2:
                    final_avg_years = st.number_input("Final Average Years",
                                                     min_value=1, max_value=10, 
                                                     value=obj.pension_params.get('final_avg_years', 3),
                                                     key=f'{income_id}_edit_final_avg',
                                                     on_change=update_pension_parameters,
                                                     args=[income_id, obj])
                    retirement_age = st.number_input("Retirement Age",
                                                   min_value=50, max_value=80, 
                                                   value=obj.pension_params.get('retirement_age', 65),
                                                   key=f'{income_id}_edit_retirement',
                                                   on_change=update_pension_parameters,
                                                   args=[income_id, obj])
                
                if hasattr(obj, 'pension'):
                    st.write(f"**Current Pension Value**: ${int(obj.pension[obj.start_year]):,}")
                
                st.button("Remove Pension", on_click=remove_pension_from_income, args=[income_id], key=f"{income_id}_remove_pension")
            else:
                # Show Add Pension button
                st.write("No pension configured")
                st.button(f"{BUTTON_ADD_PENSION} Add Pension", on_click=add_pension, args=[income_id], key=f"{income_id}_add_pension")

            st.divider()
            st.write("**Payroll Tax Add-ons**")
            if hasattr(obj, 'payroll_taxes') and obj.payroll_taxes:
                for tax_index, payroll_tax in enumerate(obj.payroll_taxes):
                    tax_name = payroll_tax.get('name', 'Payroll Tax')
                    tax_rate = payroll_tax.get('rate', 0)
                    st.write(f"{tax_name}: {tax_rate:.4f}")
                    st.button("Remove Payroll Tax",
                              on_click=remove_payroll_tax_from_income,
                              args=[income_id, tax_index],
                              key=f"{income_id}_payroll_tax_remove_{tax_index}")
            else:
                st.write("No payroll taxes configured")
            st.button("Add Payroll Tax", on_click=add_payroll_tax, args=[income_id], key=f"{income_id}_add_payroll_tax")

        st.button(f"{BUTTON_DELETE} Delete",on_click=remove_income,args=[income_id],key=f"{income_id}_del")
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


st.header('Income')
utils.ui_functions.add_colorful_divider()

col1, col2 = st.columns(2)

with col1:
    if st.session_state['income_display'] == 'Monthly':
        disp_div = 12
    elif st.session_state['income_display'] == 'Annual':
        disp_div = 1

    st.button(f"{BUTTON_ADD_INCOME} New Income ",
              use_container_width=True,
              on_click=add_income)
    
    # Remove the standalone Add Pension button - pension controls are now entirely within each income widget

    for cat in ['Earned']:
        temp_obj_list = [obj for obj in st.session_state['plan'].income if obj.category == cat and not obj.future_event]
        if len(temp_obj_list) > 0:
            st.subheader(cat)
            for obj in sorted(temp_obj_list,key = lambda x: x.value[x.start_year], reverse=True):    
                obj = st.session_state['plan'].get_object_from_id(obj.id)
                if obj.editable == True:
                    obj = generate_income(obj.id,disp_div)
                else:
                    obj = generate_static_income(obj.id,disp_div)
         
       
with col2:
    st.write('Gross Income (',st.session_state['plan'].start_year,'): ',sum([obj.value[obj.start_year] for obj in st.session_state['plan'].income if not obj.future_event]))
    st.plotly_chart(st.session_state['plan'].pie_chart('income',st.session_state['plan'].start_year,'pie'))

# Display Value toggle at bottom
st.selectbox('Display Value',
             options=['Annual','Monthly'],
             key='income_display')

