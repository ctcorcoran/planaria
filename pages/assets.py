import streamlit as st 

import pandas as pd
import plotly.express as px

import objs.plan 
import objs.financial_objects
import utils.utilities
import utils.ui_functions
from utils.emoji_config import *
import utils.generators_ui

# Setup page configuration and CSS
utils.ui_functions.setup_page()

# subcats = ['Retirement','Bonds','Savings','Automobile','Real Estate']

def add_asset_to_plan(keyword):
    utils.ui_functions.sidebar_buttons(False)
    attributes = {}
    if keyword == '401k':
        category = 'Investment'
        subcategory = 'Retirement'
        interest = False
        person = st.session_state['plan'].get_object_from_name('Person',st.session_state['paired_inc_new'].split(' - ')[1]).id
        inc_id = st.session_state['plan'].get_object_from_name('Income',st.session_state['paired_inc_new'].split(' - ')[0],person).id
        contribution = 0
    else:
        subcategory = st.session_state['subcategory_new']
        if subcategory in ['Retirement','Bonds']:
            category = 'Investment'
            interest = False
        elif subcategory in ['Savings']:
            category = 'Savings'
            interest = True
        elif subcategory in ['Automobile','Real Estate']:
            category = 'Tangible'
            interest = False
        person = st.session_state['plan'].get_object_from_name('Person',st.session_state['person_new']).id
        if st.session_state['ann_month_new'] == 'Annual':
            multi = 1 
        elif st.session_state['ann_month_new'] == 'Monthly':
            multi = 12
        contribution = multi*st.session_state['contribution_new']
        
    asset_obj = objs.financial_objects.AssetObj(person,category,subcategory,
                                                st.session_state['name_new'],
                                                st.session_state['tax_keyword_new'],
                                                st.session_state['plan'].cal_year,
                                                st.session_state['value_new'],
                                                st.session_state['growth_rate_new'],
                                                contribution,
                                                interest,
                                                True,
                                                attributes=attributes)
    
    st.session_state['plan'].assets.append(asset_obj)

    if keyword == '401k':
        st.session_state['plan'] = asset_obj.make_401k_objs(st.session_state['plan'],
                                                            inc_id,
                                                            st.session_state['props_new'],
                                                            st.session_state['match_props_max_new'])
    else:
        st.session_state['plan'] = asset_obj.make_expense_obj(st.session_state['plan'],'contribution')
    
    st.session_state['plan'] = asset_obj.project(st.session_state['plan']) 
    
    # Drawdown
    if asset_obj.category == 'Savings':
        st.session_state['plan'].drawdown_order[asset_obj.person] += [asset_obj.id]
    
    
@st.dialog('New Asset')    
def add_asset(keyword):
    if len([person for person in st.session_state['plan'].people if person.dependent == False]) > 1:
        joint = ['Joint']
    else:
        joint = []
    with st.form("new_asset"):
        st.text_input("Name",
                      key='name_new')
        if keyword != '401k':
            st.selectbox("Subcategory",
                         options=['Retirement','Savings','Bonds','Automobile','Real Estate'],
                         key='subcategory_new')
            st.selectbox("Person",
                         options=([person.name for person in st.session_state['plan'].people if person.dependent == False]+joint),
                         key='person_new')
            st.selectbox("Tax Keyword",
                         options=['','HSA'],
                         key='tax_keyword_new')
        st.number_input('Growth Rate',
                        min_value=0.0,
                        max_value=1.0,
                        value=0.0,
                        step=0.001,
                        format="%0.3g",
                        key='growth_rate_new')
        st.number_input('Value',
                        min_value=0,
                        max_value=int(1e12),
                        value=0,step=1,
                        key='value_new')
        col1, col2 = st.columns(2)
        if keyword == '401k':
            st.selectbox('Tax Keyword',
                         options = ['Traditional','Roth'],
                         key='tax_keyword_new')
            st.selectbox('Paired Income',
                         options=[inc.name+' - '+st.session_state['plan'].get_object_from_id(inc.person).name for inc in st.session_state['plan'].income if inc.subcategory == 'Salary'],
                         key='paired_inc_new')
            st.number_input('Contribution Prop. of Income',
                            min_value=0.0,
                            max_value=1.0,
                            value=0.0,
                            step=0.001,
                            format="%0.3g",
                            key='props_new')
            st.number_input('Employer Match Prop.',
                            min_value=0.0,
                            max_value=1.0,
                            value=0.0,
                            step=0.001,
                            format="%0.3g",
                            key='match_props_max_new')
        else:
            with col1:
                st.number_input("Contribution",
                                min_value=0,
                                key='contribution_new')
            with col2:
                st.radio(label='AnnMonth',
                         options=['Annual','Monthly'],
                         key='ann_month_new',
                         label_visibility='hidden')
    
        # Add Close/Discard Button! - can't be done... need custom form
        submit = st.form_submit_button(label="Add Asset to Plan",
                                       on_click=add_asset_to_plan,
                                       args=[keyword])
    if submit:
        st.rerun()

def remove_asset(asset_id):
    utils.ui_functions.sidebar_buttons(False)
    
    st.session_state["plan"].remove_object_by_id(asset_id)

def update_asset(asset_id,obj,attr):
    utils.ui_functions.sidebar_buttons(False)

    if attr == 'contribution':
        if st.session_state[f'{asset_id}_ann_month'] == 'Monthly':
            multi = 12
        else:
            multi = 1
        # May need to make this align with Liabilities...
        if st.session_state[f'{asset_id}_val_entry']=='Auto':
            setattr(obj,attr,multi*st.session_state[f"{asset_id}_"+attr])
        else:
            setattr(obj,attr,multi*pd.Series(st.session_state[f"{asset_id}_"+attr].set_axis(st.session_state[f"{asset_id}_"+attr].index.astype(int))))
        
    elif attr == 'props':
        if st.session_state[f'{asset_id}_prop_entry']=='Auto':
            setattr(obj,attr,st.session_state[f"{asset_id}_"+attr])
        else:
            setattr(obj,attr,pd.Series(st.session_state[f"{asset_id}_"+attr].set_axis(st.session_state[f"{asset_id}_"+attr].index.astype(int))))
    
    else:
        setattr(obj,attr,st.session_state[f"{asset_id}_"+attr])
        
    st.session_state['plan'] = obj.project(st.session_state['plan'])

def generate_static_asset(asset_id):    
    obj = st.session_state['plan'].get_object_from_id(asset_id)
    with st.container(border=True):
        st.write(obj.name+' ('+obj.person +') - '+str(int(obj.value[obj.start_year])))
    return(obj)

def generate_asset(asset_id):    
    obj = st.session_state['plan'].get_object_from_id(asset_id)
    if obj.person == 'Joint':
        person_name = 'Joint'
    else:
        person_name = st.session_state['plan'].get_object_from_id(obj.person).name
    with st.expander(label=(obj.name+' ('+person_name +') - '+str(int(obj.value[obj.start_year])))):
        st.write("Person: ",person_name)
        st.write("Subcategory: ",obj.subcategory)
        st.text_input("Name",
                      value=obj.name,
                      on_change=update_asset,
                      args=[asset_id,obj,'name'],
                      key=f'{asset_id}_name')
        if obj.subcategory != 'Automobile':
            st.number_input('Growth Rate',
                            min_value=0.0,
                            max_value=1.0,
                            value=obj.growth_rate[obj.start_year],
                            step=0.001,
                            format="%0.3g",
                            on_change=update_asset,
                            args=[asset_id,obj,'growth_rate'],
                            key=f'{asset_id}_growth_rate')
        st.number_input('Value',
                        min_value=0,
                        max_value=int(1e12),
                        value=int(obj.value[obj.start_year]),
                        step=1,
                        on_change=update_asset,
                        args=[asset_id,obj,'value'],
                        key=f'{asset_id}_value')

        # Indirectly get 401k objects, which should be paired with an income
        if 'Income' in [x.split('_')[0] for x in obj.paired_attr['series'].keys()]: #obj.tax_keyword == '401k':
            # Get the key for the paired income, and then get the proportions
            prop_key = [key for key, val in obj.paired_attr['series'].items() if key.split('_')[0]=='Income' and val[0][1]=='contribution'][0]
            prop = obj.paired_attr['series'][prop_key][0][2] #[val[0] for key, val in obj.paired_attr['series'].items() if key.split('_')[0]=='Income' and val[0][1]=='contribution'][2]
            # Set both auto and manual props, and default setting
            if isinstance(prop,pd.Series):
                prop_auto = prop[obj.start_year]
                prop_manual = prop
                entry_default = 1
            else:
                prop_auto = prop
                prop_manual = utils.utilities.expand_contract(prop, obj.cal_year)
                entry_default = 0
                
            st.selectbox(label='Proportion Entry',
                         options=['Auto','Manual'],
                         index=entry_default,
                         key=f'{asset_id}_prop_entry')
            
            if st.session_state[f'{asset_id}_prop_entry'] == 'Auto':
                st.number_input('Proportion',
                                min_value=0.0,
                                max_value=1.0,
                                value=prop_auto,
                                step=0.001,
                                format="%0.3g",
                                on_change=update_asset,
                                args=[asset_id,obj,'props'],
                                key=f'{asset_id}_props')
            else:
                #obj.props = st.data_editor(obj.props.set_axis(obj.value.index.astype(str)),num_rows='fixed',key=f'{asset_id}_props').set_axis(obj.props.index)
                save_props = st.button('Save Edits')
                edited_props = st.data_editor(prop_manual,#obj.props.set_axis(obj.value.index.astype(str)),
                                              num_rows='fixed',
                                              use_container_width=True,
                                              key=f'{asset_id}_props_editor')
                if save_props:
                    utils.ui_functions.sidebar_buttons(False)
                    obj.paired_attr['series'][prop_key][0][2] = edited_props.set_axis(obj.cal_year)
                    st.session_state['plan'] = obj.project(st.session_state['plan'])
                    st.rerun()

        # Don't include this editor for the first entry in each drawdown, since those contributions
        # are handled in .balance_and_tax()
        elif obj.id not in [id_list[0] for id_list in st.session_state['plan'].drawdown_order.values() if len(id_list) > 0]:
            col1, col2 = st.columns(2)
            with col1:
                st.selectbox(label='Contribution Entry',
                             options=['Auto','Manual'],
                             key=f'{asset_id}_val_entry')
            with col2:
                st.radio(label='AnnMonth',
                         options=['Annual','Monthly'],
                         key=f'{asset_id}_ann_month',
                         label_visibility='hidden')
                if st.session_state[f'{asset_id}_ann_month'] == 'Annual':
                    multi = 1 
                elif st.session_state[f'{asset_id}_ann_month'] == 'Monthly':
                    multi = 12
            if st.session_state[f'{asset_id}_val_entry'] == 'Auto':
                st.number_input("Contribution",
                                min_value=0,
                                max_value=int(1e12),
                                value=int(obj.contribution[obj.start_year]/multi),
                                step=1,
                                on_change=update_asset,
                                args=[asset_id,obj,'contribution'],
                                key=f'{asset_id}_contribution')
            else:
                st.write(f'Enter values in {obj.start_year} dollars')
                obj.contribution = st.data_editor(obj.deflate().value.set_axis(obj.value.index.astype(str))/multi,
                                                 num_rows='fixed',
                                                 on_change=update_asset,
                                                 args=[asset_id,obj,'contribution'],
                                                 key=f'{asset_id}_contribution').set_axis(obj.value.index)
        
        st.button(f"{BUTTON_DELETE} Delete",on_click=remove_asset,args=[asset_id],key=f"{asset_id}_del")
        return(obj)

### Drawdown Order

def update_drawdown_order(person_id):
    utils.ui_functions.sidebar_buttons(False)

    st.session_state['plan'].drawdown_order[person_id] = st.session_state[f'{person_id}_drawdown']

def format_drawdown_acct(acct_id):
    return(st.session_state['plan'].get_object_from_id(acct_id).name)

def generate_drawdown_selector(person_id):
    st.multiselect(label=st.session_state['plan'].get_object_from_id(person_id).name,
                   options = [obj.id for obj in st.session_state['plan'].assets if obj.category == 'Savings' and obj.person == person_id], #st.session_state['plan'].drawdown_order[person_id],
                   default = st.session_state['plan'].drawdown_order[person_id],
                   format_func=format_drawdown_acct,
                   on_change=update_drawdown_order,
                   args=[person_id],
                   key = f'{person_id}_drawdown')

### Wrappers for Home and Car

@st.dialog('Add Home')
def add_home(session_state):
    utils.generators_ui.add_asset('home',True,session_state)

@st.dialog('Add Car')    
def add_car(session_state):
    utils.generators_ui.add_asset('car',True,session_state)

############
# RUN PAGE #
############

st.session_state['plan'] = st.session_state['plan']

# SIDEBAR
utils.ui_functions.make_sidebar()

st.header('Assets')
utils.ui_functions.add_colorful_divider()

col1, col2 = st.columns(2)

with col1:

    col11,col12 = st.columns(2)
    with col11:
        st.button(f"{BUTTON_ADD_ASSET} Add Asset",
                  use_container_width=True,
                  on_click=add_asset,
                  args=[''])
        st.button(f"{BUTTON_ADD_HOME} Add Home",
                  use_container_width=True,
                  on_click=add_home,
                  args=[st.session_state])
    with col12:
        st.button(f"{BUTTON_ADD_401K} Add 401k",
                  use_container_width=True,
                  on_click=add_asset,
                  args=['401k'])
        st.button(f"{BUTTON_ADD_CAR} Add Car",
                  use_container_width=True,
                  on_click=add_car,
                  args=[st.session_state])
        
    # Get all future event object IDs (including descendants)
    future_event_ids = utils.utilities.get_future_event_object_ids(st.session_state['plan'])
    
    # Loop over each subcategory
    for subcat in ['Retirement','Savings','Bonds','Automobile','Real Estate']:
        temp_obj_list = [obj for obj in st.session_state['plan'].assets if obj.subcategory == subcat and not getattr(obj, 'ui_hidden', False) and obj.id not in future_event_ids]
        if len(temp_obj_list) > 0:
            st.subheader(subcat)
            for asset in sorted(temp_obj_list,key = lambda x: x.value[x.start_year], reverse=True):
                asset_obj = st.session_state['plan'].get_object_from_id(asset.id)
                if asset_obj.editable == True:
                    asset_obj = generate_asset(asset.id)
                else:
                    asset_obj = generate_static_asset(asset.id)
         
with col2:
    st.write('Total Assets (',st.session_state['plan'].start_year,'): ',sum([obj.value[obj.start_year] for obj in st.session_state['plan'].assets if obj.id not in future_event_ids]))
    st.plotly_chart(st.session_state['plan'].pie_chart('assets',st.session_state['plan'].start_year,'pie'))

    #

    with st.expander('Drawdown Order'):
        for person_id in list(set([obj.person for obj in st.session_state['plan'].assets if obj.category == 'Savings'])):
            generate_drawdown_selector(person_id)

