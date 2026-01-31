import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
# This should eliminate the pandas future warnings from printing,
# which seriously hampers the debugging process

import streamlit as st 
import pandas as pd

import objs.plan 
import utils.utilities
import utils.generators
import utils.ui_functions
from utils.emoji_config import *

### ASSET - ADD, FORM, GENERATE, UPDATE, REMOVE

def add_asset_to_plan(asset_type,existing,down_payment_sources,session_state):
    utils.ui_functions.sidebar_buttons(False)
        
    # Set person_id:
    if st.session_state['person_new'] == 'Joint':
        person_id = 'Joint'
    else:
        person_id = st.session_state['plan'].get_object_from_name('Person',st.session_state['person_new']).id

    # ASSET AND LIAB DICTS
    liab_dict = {'interest_rate':st.session_state['interest_rate_new'],
                 'attributes':{}}
    
    # Existing - payment
    # New - term, term_in_years, down_pct, down_payment

    if existing == False:
        # This is a bit of a mess... data_editor doesn't want to pass updates from a form
        down_payment_sources = [(down_payment_sources.loc[i,'id'],float(st.session_state['down_payment_sources_new']['edited_rows'][i]['Value/Proportion'])) for i in st.session_state['down_payment_sources_new']['edited_rows'].keys()]
    
        # Term
        if asset_type == 'home':
            term = 30
        elif asset_type == 'car':
            term = 10

        liab_dict['attributes'] |= {'term':term,
                                    'term_in_years':True,
                                    'down_pct':st.session_state['down_pct_new'],
                                    'down_payment':st.session_state['down_payment_new']}
    
    else:
        liab_dict['attributes'] |= {'payment':st.session_state['payment_new'],
                                    'present_value':st.session_state['present_value_new']}
    
    # Add PMI parameters for home, and Growth Rate
    if asset_type == 'home':
        liab_dict['attributes'] |= {'pmi_rate':0.01,
                                    'pmi_thresh_pct':0.2}
        asset_dict = {'growth_rate':st.session_state['growth_rate_new']}
        
    # Name and model_year for car - depreciation rate is computed in generator from this
    elif asset_type == 'car':
        if existing == True:
            car_name = st.session_state['name_new']
        else:
            car_name = 'Automobile'
        asset_dict = {'name':car_name,
                      'model_year':st.session_state['model_year_new']}
    
    # PARAMS
    asset_params = {'maintenance_rate':st.session_state['maintenance_rate_new'],
                    'insurance':st.session_state['insurance_new']}
    
    # Add property tax for a house
    if asset_type == 'home':
        asset_params |= {'property_tax_rate':st.session_state['property_tax_rate_new']}

    # If its a future event, expenses/assets can be replaced, and start_year
    if existing == False:
        asset_dict |= {'expenses_replaced':st.session_state['expenses_replaced_new'],
                         'assets_replaced':st.session_state['assets_replaced_new']}
        start_year = st.session_state['year_new']
    else:
        start_year = st.session_state['plan'].start_year
    
    # GENERATOR
    if asset_type == 'home':
        wrapper = utils.generators.buy_home
    elif asset_type == 'car':
        wrapper = utils.generators.buy_car

    st.session_state['plan'] = wrapper(st.session_state['plan'],
                                       person_id,
                                       start_year,
                                       st.session_state['value_new'],
                                       asset_dict,
                                       liab_dict,
                                       down_payment_sources,
                                       asset_params)

    return()

# Existing: Remaining Principal, Present Value, Loan Payment
# If Payment = 0 or Remaining Principal = 0, Don't generate a loan object
# No downpayment, or expenses replaced
    
def add_asset(asset_type,existing,session_state):
    # Define format_name inside the function, since format_func can only have one argument
    def format_name(obj_id):
        obj = st.session_state['plan'].get_object_from_id(obj_id)
        #print(obj.id,',',obj.name,',',obj.person)
        if obj.person == 'Joint':
            extra_string = ''
        else:
            extra_string = ' ('+st.session_state['plan'].get_object_from_id(obj.person).name +')'
        return(obj.name + extra_string)
    
    if len([person for person in st.session_state['plan'].people if person.dependent == False]) > 1:
        joint = ['Joint']
    else:
        joint = []
    with st.form("new_asset"):
        person_options = [person.name for person in st.session_state['plan'].people if person.dependent == False] + joint
        if asset_type == 'home' and 'Joint' in person_options:
            default_person_index = person_options.index('Joint')
        else:
            default_person_index = 0
        st.selectbox("Person",
                     options=person_options,
                     index=default_person_index,
                     key='person_new')
        if existing == True:
            if asset_type == 'car':
                st.text_input("Name",
                              key="name_new")
        # Years
        if existing == False:
            st.number_input("Purchase Year",
                            min_value=st.session_state['plan'].start_year,
                            max_value=st.session_state['plan'].start_year+st.session_state['plan'].n_years,
                            value=st.session_state['plan'].start_year,
                            step=1,
                            key="year_new")
        if asset_type == 'car':
            st.number_input("Model Year",
                            min_value=1930,
                            max_value=st.session_state['plan'].start_year+1,
                            value=st.session_state['plan'].start_year,
                            step=1,
                            key="model_year_new")
            
        # Value
        if existing == False:
            val_label = "Purchase Price"
        else:
            val_label = "Present Value"
        st.number_input(val_label,
                        min_value=0,
                        value=0,
                        step=100,
                        key="value_new")
        
        if existing == True:
            st.number_input("Loan Balance Remaining",
                            min_value=0,
                            value=0,
                            step=100,
                            key="present_value_new")
        
        # Rates
        if asset_type == 'home':
            st.number_input("Appreciation Rate",
                            min_value=0.0,
                            max_value=1.0,
                            value=0.07,
                            step=0.001,
                            format="%0.3g",
                            key="growth_rate_new")
        
        if asset_type == 'home':
            rate = 'Mortgage Rate'
        elif asset_type == 'car':
            rate = 'Interest Rate'
        st.number_input(rate,
                        min_value=0.0,
                        max_value=1.0,
                        value=0.06,
                        step=0.001,
                        format="%0.3g",
                        key="interest_rate_new")

        # Existing - Down Payment Type & Value
        if existing == False:
            col1, col2 = st.columns(2)
            with col1:
                st.number_input('Down Payment',
                                min_value=0.0,
                                max_value=1.0,
                                value = 0.1,
                                key='down_payment_new')
            with col2:
                st.text('')
                st.checkbox(label='As Proportion',value=True,key='down_pct_new')
                #st.radio(label='DownPct',options=['Value','Percent'],index=1,key='down_pct_new',label_visibility='hidden')
            st.text('Down Payment Sources')
            dp_df = pd.DataFrame([(obj.id,obj.name+' ('+st.session_state['plan'].get_object_from_id(obj.person).name+')',None) for obj in st.session_state['plan'].assets if obj.subcategory == 'Savings'],columns=['id','Name','Value/Proportion'])
            down_payment_sources = st.data_editor(dp_df,
                                                 column_config={'id':None},
                                                 disabled=['Name'],
                                                 hide_index=True,
                                                 key='down_payment_sources_new')
        
        # New - Payment
        else:
            st.number_input('Monthly Payment',
                            min_value=0,
                            value = 0,
                            step = 1,
                            key='payment_new')
            down_payment_sources = None
        
        # Asset subcategory
        if asset_type == 'home':
            subcat = 'Real Estate'
        elif asset_type == 'car':
            subcat = 'Automobile'
        
        # If New - replacement assets/expenses
        if existing == False:
            exp_replace_options = [obj.id for obj in st.session_state['plan'].expenses
                                   if obj.category == 'Necessary'
                                   and len(obj.paired_attr['series']) == 0
                                   and not obj.future_event]
            st.multiselect('Assets Replaced',
                           options = [obj.id for obj in st.session_state['plan'].assets if obj.subcategory == subcat],
                           default=None,
                           format_func=format_name,
                           key='assets_replaced_new')
            #
            st.multiselect('Expenses Replaced',
                           options = exp_replace_options,
                           default=None,
                           format_func=format_name,
                           key='expenses_replaced_new')
        
        #
        st.markdown("""---""")
        # (Tax), Maintenance, and Insurance
        if asset_type == 'home':
            st.number_input("Property Tax Rate",
                            min_value=0.0,
                            max_value=1.0,
                            value=0.01,
                            step=0.001,
                            format="%0.3g",
                            key="property_tax_rate_new")
            maintenance_default = 0.015
            insurance_default = 1500
            asset_type_ = 'Home'
        elif asset_type == 'car':
            maintenance_default = 0.1
            insurance_default = 1000
            asset_type_ = 'Car'
    
        st.number_input("Maintenance Rate",
                        min_value=0.0,
                        max_value=1.0,
                        value=maintenance_default,
                        step=0.001,
                        format="%0.3g",
                        key="maintenance_rate_new")

        st.number_input("Insurance",
                        min_value=0,
                        value=insurance_default,
                        step=10,
                        key="insurance_new")
        
        
        submit = st.form_submit_button(label="Add "+asset_type_+" + Expenses to Plan",
                              on_click=add_asset_to_plan,
                              args=[asset_type,existing,down_payment_sources,session_state])
        if submit:
            st.rerun()

def generate_asset(asset_id,session_state):
    # Define format_name inside the function, since format_func can only have one argument
    def format_name(obj_id):
        obj = st.session_state['plan'].get_object_from_id(obj_id)
        #print(obj.id,',',obj.name,',',obj.person)
        if obj.person == 'Joint':
            extra_string = ''
        else:
            extra_string = ' ('+st.session_state['plan'].get_object_from_id(obj.person).name +')'
        return(obj.name + extra_string)
    
    # Note - all streamlit objects will be identified with the asset id
    obj = st.session_state['plan'].get_object_from_id(asset_id)
    paired_ids = list(set([obj_id for pair in [x for val in st.session_state['plan'].pairs.values() for x in val] for obj_id in pair if obj_id != asset_id and asset_id in pair])) #[obj_id for lst in st.session_state['plan'].pairs for obj_id in lst if obj_id != asset_id and asset_id in lst]

    # Person
    if obj.person == 'Joint':
        person_name = 'Joint'
    else:
        person_name = st.session_state['plan'].get_object_from_id(obj.person).name
    
    # If there is a paired liability, get it
    if 'Liability' in [obj_id.split('_')[0] for obj_id in paired_ids]:
        paired_liab = True
        liab_obj = st.session_state['plan'].get_object_from_id([obj_id for obj_id in paired_ids if obj_id.split('_')[0]=='Liability'][0])
    else:
        paired_liab = False
    
    # Determine if this asset is a future event (events list is source of truth)
    asset_event = next((ev for ev in st.session_state['plan'].events
                        if ev[2] == asset_id and ev[1] in ['Buy Home','Buy Car']), None)
    is_future_event = (asset_event is not None) or obj.future_event
    event_year = int(asset_event[0]) if asset_event is not None else obj.start_year
    event_type = asset_event[1] if asset_event is not None else None

    # Determine label and emoji based on event type or subcategory (legacy-safe)
    if event_type == 'Buy Home':
        prefix = BUTTON_BUY_HOME
    elif event_type == 'Buy Car':
        prefix = BUTTON_BUY_CAR
    elif obj.subcategory in ['Real Estate','Home']:
        prefix = BUTTON_BUY_HOME
    elif obj.subcategory in ['Automobile','Car','Auto']:
        prefix = BUTTON_BUY_CAR
    else:
        prefix = BUTTON_ADD_ASSET

    if is_future_event:
        existing = False
        action_label = event_type if event_type is not None else f"Buy {obj.name}"
        expander_label = f"({event_year}) {prefix} {action_label}"
    else:
        existing = True
        expander_label = f"{BUTTON_ADD_ASSET} {obj.name} (and Expenses)"

    with st.expander(label=expander_label):
        st.write("Person",person_name)
        
        # Year
        if existing == False:
            st.number_input("Purchase Year",
                            min_value=st.session_state['plan'].start_year,
                            max_value=st.session_state['plan'].start_year+st.session_state['plan'].n_years,
                            value=event_year,
                            step=1,
                            on_change=update_asset,
                            args=[[asset_id]+paired_ids,'start_year',session_state],
                            key=f"{asset_id}_start_year")
        
        # Value
        if existing == False:
            val_label = "Purchase Price"
        else:
            val_label = "Present Value"
            
        st.number_input(val_label,
                        min_value=0.0,
                        value=float(obj.value[obj.start_year]),
                        step=100.0,
                        on_change=update_asset,
                        args=[[asset_id]+paired_ids,'value',session_state],
                        key=f"{asset_id}_value")
        
        if paired_liab == True and existing == True:
            st.number_input("Loan Balance Remaining",
                            min_value=0.0,
                            value=float(liab_obj.value[liab_obj.start_year]),
                            step=100.0,
                            on_change=update_asset,
                            args=[[asset_id]+paired_ids,'present_value',session_state],
                            key=f"{asset_id}_present_value")

        # Rates
        if obj.subcategory == 'Real Estate':
            st.number_input("Appreciation Rate",
                            min_value=0.0,
                            max_value=1.0,
                            value=obj.growth_rate[obj.start_year],
                            step=0.001,
                            format="%0.3g",
                            on_change=update_asset,
                            args=[[asset_id]+paired_ids,'growth_rate',session_state],
                            key=f"{asset_id}_growth_rate")
            rate = 'Mortgage Rate'
            
        elif obj.subcategory == 'Automobile':
            rate = 'Interest Rate'
        
        if paired_liab == True:
            st.number_input(rate,
                            min_value=0.0,
                            max_value=1.0,
                            value=0.06,
                            step=0.001,
                            format="%0.3g",
                            on_change=update_asset,
                            args=[[asset_id]+paired_ids,'interest_rate',session_state],
                            key=f"{asset_id}_interest_rate")
        
        # Existing - Down Payment Type & Valueapp
        if existing == False:
            if paired_liab == True:
                # Down Payment Type & Value
                col1, col2 = st.columns(2)
                with col1:
                    if liab_obj.down_pct == True:
                        val = round(liab_obj.down_payment,2)
                        min_val = 0.0
                        max_val = 1.0
                    else:
                        val = int(liab_obj.down_payment)
                        min_val = 0
                        max_val = int(1e12)
                    st.number_input('Down Payment',
                                    min_value = min_val,
                                    max_value = max_val,
                                    value = val,
                                    on_change=update_asset,
                                    args=[[asset_id]+paired_ids,'down_payment',session_state],
                                    key=f'{asset_id}_down_payment')
                with col2:
                    st.text('')
                    st.checkbox(label='As Proportion',
                                value=liab_obj.down_pct,
                                on_change=update_asset,
                                args=[[asset_id]+paired_ids,'down_pct',session_state],
                                key=f'{asset_id}_down_pct')
                    
                down_payment_sources = liab_obj.down_payment_sources
                # exp_replace_options =  #[obj_.id for obj_ in st.session_state['plan'].expenses if (obj_.category == 'Necessary' and obj_.id not in paired_ids+[pair[1] for pair in st.session_state['plan'].pairs['series'] if pair[0] == liab_obj.id]) or (obj_.id in paired_ids and obj_.paired_attr['time'][asset_id][0][2]==-1)]
            else:
                # exp_replaced_options = []
                down_payment_sources = obj.down_payment_sources

            st.text('Down Payment Sources')
            #
            savings_ids = [asset.id for asset in st.session_state['plan'].assets if asset.subcategory == 'Savings']
            down_payment_sources = [pair for pair in down_payment_sources if pair[0] in savings_ids]
            dp_df = pd.DataFrame(down_payment_sources,columns=['id','Value/Proportion'])
            dp_df = pd.concat([dp_df,pd.DataFrame([(obj_.id,None) for obj_ in st.session_state['plan'].assets if obj_.subcategory == 'Savings' and obj_.id not in list(dp_df['id'])],
                                                  columns=['id','Value/Proportion'])]).reset_index(drop=True)
            dp_df.loc[:,'Name'] = dp_df.loc[:,'id'].apply(format_name)
            #
            down_payment_sources = st.data_editor(dp_df[['id','Name','Value/Proportion']],
                           column_config={'id':None},
                           disabled=['Name'],
                           hide_index=True,
                           on_change=update_asset,
                           args=[[asset_id]+paired_ids,'down_payment_sources',session_state],
                           key=f'{asset_id}_down_payment_sources')
            updated_sources = [(down_payment_sources.loc[i,'id'],down_payment_sources.loc[i,'Value/Proportion']) for i in range(len(down_payment_sources))]
            updated_sources = [pair for pair in updated_sources if pair[0] in savings_ids]
            if paired_liab == True:
                liab_obj.down_payment_sources = updated_sources
            else:
                obj.down_payment_sources = updated_sources
            
            # If New - replacement assets/expenses
            st.multiselect('Assets Replaced',
                           options = [obj_.id for obj_ in st.session_state['plan'].assets if (obj_.subcategory == obj.subcategory and obj_.id != obj.id)],
                           default = [obj_.id for obj_ in st.session_state['plan'].assets if asset_id in obj_.paired_attr['time'].keys() if obj_.id in paired_ids and obj_.paired_attr['time'][asset_id][0][2]==-1],
                           format_func=format_name,
                           on_change=update_asset,
                           args=[[asset_id]+paired_ids,'assets_replaced',session_state],
                           key=f'{asset_id}_assets_replaced')
            exp_replace_options = [obj.id for obj in st.session_state['plan'].expenses
                                   if obj.category == 'Necessary'
                                   and len(obj.paired_attr['series']) == 0
                                   and not obj.future_event]
            st.multiselect('Expenses Replaced',
                           options = exp_replace_options,
                           default = [obj_.id for obj_ in st.session_state['plan'].expenses if obj_.id in paired_ids and obj_.paired_attr['time'][asset_id][0][2]==-1],
                           format_func=format_name,
                           on_change=update_asset,
                           args=[[asset_id]+paired_ids,'expenses_replaced',session_state],
                           key=f'{asset_id}_expenses_replaced')
            
        # New - Payment
        else:
            if paired_liab == True:
                st.number_input('Monthly Payment',
                                min_value=0.0,
                                value=float(liab_obj.payment),
                                step=1.0,
                                on_change=update_asset,
                                args=[[asset_id]+paired_ids,'payment',session_state],
                                key=f'{asset_id}_payment')
        
        #
        st.markdown("""---""")
        # Maintenance, Tax, and Insurance
        if obj.subcategory == 'Real Estate':
            # Get Property Tax Object and Rate
            tax_obj = [obj_ for obj_ in st.session_state['plan'].expenses if (obj.id in [key for inner_dict in obj_.paired_attr.values() for key in inner_dict.keys()] and 'Property Tax' in obj_.name)][0]
            if isinstance(tax_obj.paired_attr['series'][asset_id][0][2],pd.Series):
                tax_rate = tax_obj.paired_attr['series'][asset_id][0][2][tax_obj.start_year]
            else:
                tax_rate = tax_obj.paired_attr['series'][asset_id][0][2]
                
            st.number_input("Property Tax Rate",
                            min_value=0.0,
                            max_value=1.0,
                            value=tax_rate,
                            step=0.001,
                            format="%0.3g",
                            on_change=update_asset,
                            args=[[asset_id]+paired_ids,'property_tax_rate',session_state],
                            key=f"{asset_id}_property_tax_rate")
        # Get Maintenance Object and Rate
        maint_obj = [obj_ for obj_ in st.session_state['plan'].expenses if (obj.id in [key for inner_dict in obj_.paired_attr.values() for key in inner_dict.keys()] and 'Maintenance' in obj_.name)][0]
        if isinstance(maint_obj.paired_attr['series'][asset_id][0][2],pd.Series):
            maint_rate = maint_obj.paired_attr['series'][asset_id][0][2][maint_obj.start_year]
        else:
            maint_rate = maint_obj.paired_attr['series'][asset_id][0][2]    
        st.number_input("Maintenance Rate",
                        min_value=0.0,
                        max_value=1.0,
                        value=maint_rate,
                        step=0.001,
                        format="%0.3g",
                        on_change=update_asset,
                        args=[[asset_id]+paired_ids,'maintenance_rate',session_state],
                        key=f"{asset_id}_maintenance_rate")
        
        # Get Insurance Object and Value
        ins_obj = [obj_ for obj_ in st.session_state['plan'].expenses if (obj.id in [key for inner_dict in obj_.paired_attr.values() for key in inner_dict.keys()] and 'Insurance' in obj_.name)][0]
        
        st.number_input("Insurance",
                        min_value=0.0,
                        value=float(ins_obj.value_input[ins_obj.start_year]),
                        step=10.0,
                        on_change=update_asset,
                        args=[[asset_id]+paired_ids,'insurance',session_state],
                        key=f"{asset_id}_insurance")
        
        # Delete button
        if paired_liab == True:
            del_args = [[asset_id,liab_obj.id],session_state]
        else:
            del_args = [[asset_id,None],session_state]
        st.button(f"{BUTTON_DELETE} Delete",
                  on_click=remove_asset,
                  args=del_args,
                  key=f"{asset_id}_del")

    return()

def update_asset(id_list,attr,session_state):
    utils.ui_functions.sidebar_buttons(False)
    
    asset_id = id_list[0]
    asset_obj = st.session_state['plan'].get_object_from_id(asset_id)
  
    # Determine if a future addition
    if asset_obj.future_event:
        existing = False
    else:
        existing = True  
  
    # If there is a paired liability, get it
    liab_ids = [obj_id for obj_id in id_list if obj_id.split('_')[0] == 'Liability']
    if len(liab_ids) > 0:
        paired_liab = True
        liab_obj = st.session_state['plan'].get_object_from_id(liab_ids[0])
    else:
        paired_liab = False
        
    if attr == 'start_year':
        start_year = st.session_state[f'{asset_id}_start_year']
        
        # Update plan.events, if future purchase
        st.session_state['plan'].events = [[start_year,x[1],x[2]] if x[2]==asset_id else (x[0],x[1],x[2]) for x in st.session_state['plan'].events]
        
        # Update asset
        old_start_year = asset_obj.start_year
        asset_obj.value = asset_obj.value[asset_obj.start_year]
        asset_obj.start_year = start_year
    
        # Update downpayments
        # If there is a liability, get down payment from it
        if paired_liab == True:
            down_payment_sources = liab_obj.down_payment_sources
            if liab_obj.down_pct == True:
                down_payment = liab_obj.down_payment * liab_obj.principal
            else:
                down_payment = liab_obj.down_payment
            old_start_year = liab_obj.start_year
        
        # If no liability, asset holds down_payment_sources
        else:
            down_payment = asset_obj.value[start_year]
            down_payment_sources = asset_obj.down_payment_sources

        for pair in down_payment_sources:
            st.session_state['plan'].get_object_from_id(pair[0]).deposit(down_payment*pair[1],old_start_year)
            st.session_state['plan'].get_object_from_id(pair[0]).withdrawal(down_payment*pair[1],start_year)
            
        # Update object start_year
        if paired_liab == True:
            liab_obj.start_year = start_year
        else:
            asset_obj.start_year = start_year

        # Ensure dependent projections fire when start year changes
        if any(pair[0] == asset_id for lst in st.session_state['plan'].pairs.values() for pair in lst):
            asset_obj.dependent_objs = True
    
    elif attr == 'value':
        asset_obj.value = st.session_state[f'{asset_id}_value']
        
        if paired_liab == True and existing == False:
            liab_obj.principal = st.session_state[f'{asset_id}_value']

    elif attr == 'present_value':
        liab_obj.value = st.session_state[f'{asset_id}_present_value']

    elif attr == 'interest_rate':
        liab_obj.interest_rate = st.session_state[f'{asset_id}_interest_rate']
        
    elif attr == 'growth_rate':
        asset_obj.growth_rate = st.session_state[f'{asset_id}_growth_rate']
        
    elif attr == 'down_payment':
        # First, calculate the the down_payment
        if liab_obj.down_pct == True:
            down_payment_old = liab_obj.down_payment * liab_obj.principal
            down_payment = st.session_state[f'{asset_id}_down_payment'] * liab_obj.principal
        else:
            down_payment_old = liab_obj.down_payment
            down_payment = st.session_state[f'{asset_id}_down_payment']
            
        # Next, deposit the old and withdraw the new    
        for pair in liab_obj.down_payment_sources:
            st.session_state['plan'].get_object_from_id(pair[0]).deposit(down_payment_old*pair[1],liab_obj.start_year)
            st.session_state['plan'].get_object_from_id(pair[0]).withdrawal(down_payment*pair[1],liab_obj.start_year)
            
        # Finally, set the new attribute
        liab_obj.down_payment = st.session_state[f'{asset_id}_down_payment']
        
    elif attr == 'down_pct':
        liab_obj.down_pct = st.session_state[f'{asset_id}_down_pct']
        
    elif attr == 'down_payment_sources':
        if paired_liab == True:
            old_down_payment_sources = liab_obj.down_payment_sources
            new_down_payment_sources = liab_obj.down_payment_sources
            year = liab_obj.start_year
        else:
            old_down_payment_sources = asset_obj.down_payment_sources
            new_down_payment_sources = asset_obj.down_payment_sources
            year = asset_obj.start_year
        savings_ids = [asset.id for asset in st.session_state['plan'].assets if asset.subcategory == 'Savings']
            
        # First, copy the old down_payment_sources, and update with data_editor 
        editor_state = st.session_state.get(f'{asset_id}_down_payment_sources')
        if isinstance(editor_state, pd.DataFrame):
            new_down_payment_sources = [
                (row['id'], row['Value/Proportion'])
                for _, row in editor_state.iterrows()
                if row['Value/Proportion'] is not None
            ]
        elif isinstance(editor_state, dict) and 'edited_rows' in editor_state:
            for _, row_data in editor_state['edited_rows'].items():
                source_id = row_data.get('id')
                value = row_data.get('Value/Proportion')
                if source_id is None:
                    continue
                if value is None:
                    new_down_payment_sources = [x for x in new_down_payment_sources if x[0] != source_id]
                else:
                    new_down_payment_sources = [(x[0],x[1]) if x[0] != source_id else (x[0],value) for x in new_down_payment_sources]

        # Then, calculate the the down_payment
        if paired_liab == True:
            if liab_obj.down_pct == True:
                down_payment = liab_obj.down_payment * liab_obj.principal
            else:
                down_payment = liab_obj.down_payment
        else:
            down_payment = asset_obj.value[asset_obj.start_year]
            
        # Next, deposit the old  
        for pair in old_down_payment_sources:
            st.session_state['plan'].get_object_from_id(pair[0]).deposit(down_payment*pair[1],year)
        
        # Then, withdraw the new
        for pair in new_down_payment_sources:
            st.session_state['plan'].get_object_from_id(pair[0]).withdrawal(down_payment*pair[1],year)
            
        # Finally, set the new attribute
        new_down_payment_sources = [pair for pair in new_down_payment_sources if pair[0] in savings_ids]
        if paired_liab == True:
            liab_obj.down_payment_sources = new_down_payment_sources
        else:
            asset_obj.down_payment_sources = new_down_payment_sources

    elif attr == 'assets_replaced':
        # Get previously replaced asset - should just be one, but not enforced at the moment
        # Compare to new replacement list - we'll use the -1 start/end for replacements
        
        old_replaced = [obj_id for obj_id in [x[1] for x in st.session_state['plan'].pairs['time'] if x[0] == asset_id] if st.session_state['plan'].get_object_from_id(obj_id).paired_attr['time'][asset_id][0][2] == -1]
        new_replaced = st.session_state[f'{asset_id}_assets_replaced']
        to_add = [x for x in new_replaced if x not in old_replaced]
        to_remove = [x for x in old_replaced if x not in new_replaced]
        
        # Remove pairings
        for obj_id in to_remove:
            obj = st.session_state['plan'].get_object_from_id(obj_id)
            
            # Remove asset_id's paired_attr
            obj.paired_attr['time'] = {key:obj.paired_attr['time'][key] for key in obj.paired_attr['time'].keys() if key != asset_id}
                
            # Reset end_year
            obj.end_year = max(obj.cal_year)
            
            # Remove from plan.pairs and project
            st.session_state['plan'].pairs['time'].remove([asset_id,obj_id])
            st.session_state['plan'] = obj.project(st.session_state['plan'])
        
        # Add new pairings
        for obj_id in to_add:
            obj = st.session_state['plan'].get_object_from_id(obj_id)
            obj.end_year = asset_obj.start_year-1
            obj.paired_attr['time'] |= {asset_id:[['start_year','end_year',-1]]}
            if [asset_id,obj_id] not in st.session_state['plan'].pairs['time']:
                st.session_state['plan'].pairs['time'].append([asset_id,obj_id])
            st.session_state['plan'] = obj.project(st.session_state['plan'])
        
    elif attr == 'expenses_replaced':
        # Get previously replaced expenses, which are paired expenses that aren't maintenace
        # property_tax, or insurance. Compare to new replacement list - we'll
        # use the -1 start/end for replacements
        old_replaced = [obj_id for obj_id in [x[1] for x in st.session_state['plan'].pairs['time'] if x[0] == asset_id] if st.session_state['plan'].get_object_from_id(obj_id).paired_attr['time'][asset_id][0][2] == -1]
        new_replaced = st.session_state[f'{asset_id}_expenses_replaced']
        to_add = [x for x in new_replaced if x not in old_replaced]
        to_remove = [x for x in old_replaced if x not in new_replaced]
        
        # Remove pairings
        for obj_id in to_remove:
            obj = st.session_state['plan'].get_object_from_id(obj_id)
            
            # Remove asset_id's paired_attr
            obj.paired_attr['time'] = {key:val for key, val in obj.paired_attr['time'].items() if key != asset_id}
                
            # Reset end_year
            obj.end_year = max(obj.cal_year)
            
            # Remove from plan.pairs and project
            st.session_state['plan'].pairs['time'].remove([asset_id,obj_id])
            st.session_state['plan'] = obj.project(st.session_state['plan'])
        
        # Add new pairings
        for obj_id in to_add:
            obj = st.session_state['plan'].get_object_from_id(obj_id)
            obj.end_year = asset_obj.start_year-1
            obj.paired_attr['time'] |= {asset_id:[['start_year','end_year',-1]]}
            if [asset_id,obj_id] not in st.session_state['plan'].pairs['time']:
                st.session_state['plan'].pairs['time'].append([asset_id,obj_id])
            st.session_state['plan'] = obj.project(st.session_state['plan'])
        
    elif attr == 'maintenance_rate':
        maintenance_obj = [obj for obj in st.session_state['plan'].expenses if obj.id in id_list and 'Maintenance' in obj.name][0]
        maintenance_obj.paired_attr['series'][asset_id][2] = st.session_state[f'{asset_id}_maintenance_rate']
        
    elif attr == 'property_tax_rate':
        property_tax_obj = [obj for obj in st.session_state['plan'].expenses if obj.id in id_list and 'Property Tax' in obj.name][0]
        property_tax_obj.paired_attr['series'][asset_id][2] = st.session_state[f'{asset_id}_property_tax_rate']
        
    elif attr == 'home_insurance':
        insurance_obj = [obj for obj in st.session_state['plan'].expenses if obj.id in id_list and 'Insurance' in obj.name][0]
        insurance_obj.paired_attr['series'][asset_id][2] = st.session_state[f'{asset_id}_home_insurance']
        
    # Project liability (conditional on its existence - asset if not), which then projects all dependent objects
    # if paired_liab == True:
    #     st.session_state['plan'] = liab_obj.project(st.session_state['plan'])
    # else:
    #     st.session_state['plan'] = asset_obj.project(st.session_state['plan'])
    st.session_state['plan'] = asset_obj.project(st.session_state['plan'])

    return()

def remove_asset(id_list,session_state):
    utils.ui_functions.sidebar_buttons(False)
    
    asset_id = id_list[0]
    liab_id = id_list[1]
    
    # Remove pairings with existing replaced expenses
    for obj_id in st.session_state[f'{asset_id}_expenses_replaced']:
        obj = st.session_state['plan'].get_object_from_id(obj_id)
        
        # Pair should only be in 'time' - objects in both 'series' and 'time' are removed with the liability
        obj.paired_attr['time'] = {key:val for key, val in obj.paired_attr['time'].items() if key != asset_id}
    
        # Reset end_year
        obj.end_year = max(obj.cal_year)
        
        # Remove from plan.pairs and project
        st.session_state['plan'].pairs['time'].remove([asset_id,obj_id])        
        st.session_state['plan'] = obj.project(st.session_state['plan'])
    
    # If it exists, emove liability, which in principle should remove everything else
    # if liab_id is not None:
    #     st.session_state['plan'].remove_object_by_id(liab_id)
    # else:
    #     st.session_state['plan'].remove_object_by_id(asset_id)
    st.session_state['plan'].remove_object_by_id(asset_id)    
        
    # Remove event, if it exists
    st.session_state['plan'].events = [ev for ev in st.session_state['plan'].events if ev[2] != asset_id]
    
    return()



### CHILD - ADD, FORM, GENERATE, UPDATE, REMOVE

def add_child_to_plan(session_state):
    utils.ui_functions.sidebar_buttons(False)
    
    # Get child name and birth year
    child_name = st.session_state['child_name_new']
    birth_year = st.session_state['birth_year_new']
    
    # Recalculate income group based on current birth year
    usda_data = pd.read_csv('data/USDA_2015_Child_Costs.csv')
    income_groups = sorted(usda_data['Salary'].unique())
    
    # Calculate total salary income for the birth year
    total_salary = 0
    for income_obj in st.session_state['plan'].income:
        if income_obj.subcategory == 'Salary':
            # Get the salary value for the birth year
            if birth_year in income_obj.value.index:
                total_salary += income_obj.value[birth_year]
    
    # Find the closest income group
    income_group = min(income_groups, key=lambda x: abs(x - total_salary))
    
    # Load USDA data and subset for income group
    input_df = usda_data[usda_data['Salary'] == income_group].copy()
    
    # Create child and expenses
    st.session_state['plan'] = utils.generators.create_child(st.session_state['plan'], 
                                                            child_name, 
                                                            birth_year, 
                                                            input_df)
    
    # Add child birth to events with income group
    st.session_state['plan'].events.append([birth_year, 'Have Child', child_name])
    
    return()

def add_child(session_state):

    with st.form("new_child"):
        st.text_input("Child Name",
                      key="child_name_new")
        
        birth_year_input = st.number_input("Birth Year",
                        min_value=st.session_state['plan'].start_year,
                        max_value=st.session_state['plan'].start_year + st.session_state['plan'].n_years,
                        value=st.session_state['plan'].start_year,
                        step=1,
                        key="birth_year_new")
        
        submit = st.form_submit_button(label="Add Child + Expenses to Plan",
                                      on_click=add_child_to_plan,
                                      args=[session_state])
        if submit:
            st.rerun()

def update_child_name(child_id, session_state):
    utils.ui_functions.sidebar_buttons(False)
    
    # Update the child's name in the plan and in the events
    new_name = st.session_state[f'{child_id}_edit_name']
    child = session_state['plan'].get_object_from_id(child_id)
    child.name = new_name
    # Update events
    for event in session_state['plan'].events:
        if event[1] == 'Have Child' and event[2] == child.name:
            event[2] = new_name

def generate_child(child_name, session_state):
    # Get child object
    child = session_state['plan'].get_object_from_name('Person', child_name)
    # Get birth year from events
    birth_year = None
    for event in session_state['plan'].events:
        if event[1] == 'Have Child' and event[2] == child_name:
            birth_year = event[0]
            break
    
    # Use the child's stored DataFrame, or create default if not exists
    if child.child_cost_df is not None:
        editor_df = child.child_cost_df.copy()
    else:
        # Fallback to default USDA data (shouldn't happen in normal flow)
        usda_data = pd.read_csv('data/USDA_2015_Child_Costs.csv')
        income_group = usda_data['Salary'].max()  # default to highest
        for event in session_state['plan'].events:
            if event[1] == 'Have Child' and event[2] == child_name:
                if len(event) > 3:  # Check if income group was stored
                    income_group = event[3]
                break
        editor_df = usda_data[usda_data['Salary'] == income_group].copy()
        child.child_cost_df = editor_df.copy()
    
    with st.expander(label=f"({birth_year}) {BUTTON_HAVE_CHILD} {child.name} - Child Expenses"):
        # Editable child name
        st.text_input("Child Name", value=child.name, key=f"{child.id}_edit_name", on_change=update_child_name, args=[child.id, session_state])
        st.write(f"Birth Year: {birth_year}")
        # Create editable dataframe for child costs (hide index and salary column)
        st.write("Child Cost Estimates (editable):")
        edited_df = st.data_editor(editor_df,
                                  key=f"{child.id}_costs",
                                  on_change=update_child_costs,
                                  args=[child.id, session_state],
                                  hide_index=True,
                                  column_config={'Salary': None})
        # Delete button
        st.button(f"{BUTTON_DELETE_CHILD} Delete Child",
                  on_click=remove_child,
                  args=[child_name, session_state],
                  key=f"{child_name}_del")
    return()

def update_child_costs(child_id, session_state):
    utils.ui_functions.sidebar_buttons(False)
    
    # Get child object
    child = session_state['plan'].get_object_from_id(child_id)
    
    # Get the edited dataframe from session state
    edited_data = st.session_state[f"{child_id}_costs"]['edited_rows']

    # Convert the edited data back to a DataFrame if needed
    if isinstance(edited_data, dict):
        # Get the original DataFrame from the child object
        original_df = child.child_cost_df.copy()
        
        # Apply the edits from the data editor
        edited_df = original_df.copy()
        for row_idx, row_data in edited_data.items():
            if isinstance(row_data, dict):
                for col_name, new_value in row_data.items():
                    if col_name in edited_df.columns and new_value is not None:
                        edited_df.loc[int(row_idx), col_name] = new_value

    else:
        # If it's already a DataFrame, use it directly
        edited_df = edited_data
    
    # Update the child's DataFrame
    child.child_cost_df = edited_df.copy()
    
    # Update child expenses with new costs
    st.session_state['plan'] = utils.generators.edit_child_expenses(st.session_state['plan'], 
                                                                   child.name, 
                                                                   edited_df)
    
    return()

def remove_child(child_name, session_state):
    utils.ui_functions.sidebar_buttons(False)
    
    # Get child object
    child = st.session_state['plan'].get_object_from_name('Person', child_name)
    
    # Remove child expenses
    child_expenses = [obj for obj in st.session_state['plan'].expenses 
                     if obj.subcategory == 'Child' and child.id in obj.child_components]
    
    for expense in child_expenses:
        # Remove this child's component from the expense
        if child.id in expense.child_components:
            del expense.child_components[child.id]
            
            # If no more children, remove the expense entirely
            if len(expense.child_components) == 0:
                st.session_state['plan'].remove_object_by_id(expense.id)
            else:
                # Recalculate the expense without this child
                st.session_state['plan'] = expense.project(st.session_state['plan'])
    
    # Remove child from people list
    st.session_state['plan'].people = [person for person in st.session_state['plan'].people 
                                      if person.id != child.id]
    
    # Remove event
    st.session_state['plan'].events = [ev for ev in st.session_state['plan'].events 
                                      if not (ev[1] == 'Have Child' and ev[2] == child_name)]
    
    return()
    
### COMBINE EXPENSES - ADD, GENERATE, APPLY, REMOVE

def get_combinable_expense_names(plan):
    # Non-joint NECESSARY expenses grouped by name; combinable if >=2 unique persons
    non_joint = [obj for obj in plan.expenses if obj.person != 'Joint' and obj.category == 'Necessary']
    name_to_people = {}
    for obj in non_joint:
        name_to_people.setdefault(obj.name, set()).add(obj.person)
    candidates = {name for name, people in name_to_people.items() if len(people) >= 2}
    # Omit names that already have a Joint expense (Necessary)
    joint_names = {obj.name for obj in plan.expenses if obj.person == 'Joint' and obj.category == 'Necessary'}
    return sorted(list(candidates - joint_names))

def combine_expenses_create_event(session_state, year):
    plan = session_state['plan']
    names = get_combinable_expense_names(plan)
    if len(names) == 0:
        return
    plan.events.append([int(year), 'Combine Expenses', {'names': names}])
    # Mark plan as needing update
    utils.ui_functions.sidebar_buttons(False)
    return

def generate_combine_expenses(event_triple, session_state):
    year = int(event_triple[0])
    payload = event_triple[2]
    names = payload.get('names', [])
    label = f"({year}) {BUTTON_COMBINE_EXPENSES} Combine Expenses"
    with st.expander(label=label):
        # Year selector (matches other future event patterns)
        key_year = "combine_year"
        st.number_input(
            "Combine Year",
            min_value=session_state['plan'].start_year,
            max_value=session_state['plan'].start_year + session_state['plan'].n_years,
            value=year,
            step=1,
            on_change=update_combine_event_year,
            key=key_year,
        )
        st.write("Names:", ", ".join(names) if names else "(none)")
        st.button(
            f"{BUTTON_DELETE} Delete",
            on_click=remove_combine_event,
            args=[payload, session_state],
            key=f"combine_expenses_del_{hash(str(names))}"
        )
    return()

def update_combine_event_year():
    new_year = int(st.session_state.get('combine_year', st.session_state['plan'].start_year))
    plan = st.session_state['plan']
    for i, ev in enumerate(plan.events):
        if ev[1] == 'Combine Expenses':
            plan.events[i][0] = new_year
            break
    st.session_state['plan'] = plan
    # Mark plan as needing update
    utils.ui_functions.sidebar_buttons(False)
    return()

def remove_combine_event(payload, session_state):
    # Remove the first matching Combine Expenses event with same payload
    plan = session_state['plan']
    # Reverse combination
    names = payload.get('names', [])
    plan = plan.uncombine_expenses(names)
    # Remove matching event
    for ev in list(plan.events):
        if ev[1] == 'Combine Expenses' and ev[2] == payload:
            plan.events.remove(ev)
            break
    session_state['plan'] = plan
    # Mark plan as needing update
    utils.ui_functions.sidebar_buttons(False)
    return()

### MARRIAGE EVENT - ADD, GENERATE, UPDATE, REMOVE

def marriage_create_event(session_state, year, budget, sources):
    session_state['plan'].events.append([int(year), 'Get Married', {'budget': int(budget), 'sources': sources}])
    # Mark plan as needing update
    utils.ui_functions.sidebar_buttons(False)
    return

def generate_marriage_event(event_triple, session_state):
    year = int(event_triple[0])
    payload = event_triple[2]
    budget = int(payload.get('budget', 0))
    sources = payload.get('sources', [])
    label = f"({year}) {BUTTON_GET_MARRIED} Marriage"
    with st.expander(label=label):
        key_year = "marriage_year"
        key_budget = "marriage_budget"
        st.number_input("Marriage Year",
                        min_value=session_state['plan'].start_year,
                        max_value=session_state['plan'].start_year + session_state['plan'].n_years,
                        value=year,
                        step=1,
                        on_change=update_marriage_event,
                        key=key_year)
        st.number_input("Wedding Budget",
                        min_value=0,
                        value=budget,
                        step=100,
                        on_change=update_marriage_event,
                        key=key_budget)
        # Sources editor
        plan = session_state['plan']
        savings_assets = [obj for obj in plan.assets if obj.subcategory == 'Savings']
        existing = pd.DataFrame(sources, columns=['id','Proportion']) if len(sources)>0 else pd.DataFrame(columns=['id','Proportion'])
        # Include Person column for clarity
        base = pd.DataFrame(
            [
                (obj.id, obj.name, (session_state['plan'].get_object_from_id(obj.person).name if obj.person != 'Joint' else 'Joint'))
                for obj in savings_assets
            ],
            columns=['id','Name','Person']
        )
        merged = base.merge(existing, on='id', how='left')
        key_sources = "marriage_sources"
        edited = st.data_editor(
            merged[['id','Name','Person','Proportion']],
            column_config={'id':None},
            disabled=['Name','Person'],
            hide_index=True,
            on_change=update_marriage_event,
            key=key_sources,
        )
        st.button(
            f"{BUTTON_DELETE} Delete",
            on_click=remove_marriage_event,
            args=[event_triple, session_state],
            key=f"marriage_del_{hash(str(payload))}"
        )
    return()

def update_marriage_event():
    # Single update function to read current widget values and update the single marriage event
    new_year = int(st.session_state.get('marriage_year', st.session_state['plan'].start_year))
    new_budget = int(st.session_state.get('marriage_budget', 0))
    edited = st.session_state.get('marriage_sources', None)
    if edited is not None:
        sources = []
        for i in range(len(edited)):
            prop = edited.loc[i,'Proportion']
            if prop is not None and prop != 0:
                sources.append((edited.loc[i,'id'], float(prop)))
    else:
        sources = []
    # Update the event in plan.events
    plan = st.session_state['plan']
    for i, ev in enumerate(plan.events):
        if ev[1] == 'Get Married':
            plan.events[i][0] = new_year
            plan.events[i][2]['budget'] = new_budget
            plan.events[i][2]['sources'] = sources
            break
    st.session_state['plan'] = plan
    # Mark plan as needing update
    utils.ui_functions.sidebar_buttons(False)
    return()

def remove_marriage_event(event_triple, session_state):
    plan = session_state['plan']
    year = int(event_triple[0])
    payload = event_triple[2]
    # Reset transactions for specified sources at the event year to 0 (idempotent cleanup)
    for (asset_id, _) in payload.get('sources', []):
        asset = plan.get_object_from_id(asset_id)
        if asset and hasattr(asset, 'transaction') and year in asset.transaction.index:
            asset.transaction[year] = 0
            plan = asset.project(plan)
    # Remove the event
    plan.events.remove(event_triple)
    session_state['plan'] = plan
    # Mark plan as needing update
    utils.ui_functions.sidebar_buttons(False)
    return()
