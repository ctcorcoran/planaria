import streamlit as st 
import pandas as pd

# import objs.plan 
import utils.utilities
import utils.generators_ui
import utils.ui_functions
from utils.emoji_config import *

# Setup page configuration and CSS
utils.ui_functions.setup_page()

# CHILD

@st.dialog('Have Child')
def add_child():
    utils.generators_ui.add_child(st.session_state)

# Use new prune mechanic with end_year

@st.dialog('Combine Expenses')
def add_combine_expenses(session_state):
    plan = session_state['plan']
    names = utils.generators_ui.get_combinable_expense_names(plan)
    with st.form("combine_expenses_form"):
        st.write("The following expense names will be combined into Joint expenses:")
        if len(names) == 0:
            st.info("No combinable expenses found (need same name across different people).")
        else:
            st.write(", ".join(names))
        year = st.number_input(
            "Combine Year",
            min_value=plan.start_year,
            max_value=plan.start_year + plan.n_years,
            value=plan.start_year,
            step=1,
            key="combine_expenses_year",
        )
        submit = st.form_submit_button("Add Combine Event")
    if submit and len(names) > 0:
        utils.generators_ui.combine_expenses_create_event(session_state, year)
        st.rerun()

    
@st.dialog('New Home')
def add_new_home(session_state):
    utils.generators_ui.add_asset('home',False,session_state)

@st.dialog('New Car')    
def add_new_car(session_state):
    utils.generators_ui.add_asset('car',False,session_state)
    
# @st.dialog('Existing Home')
# def add_existing_home(session_state):
#     utils.generators_ui.add_asset('home',True,session_state)

# @st.dialog('Existing Car')    
# def add_existing_car(session_state):
#     utils.generators_ui.add_asset('car',True,session_state)

############
# RUN PAGE #
############

st.session_state['plan'] = st.session_state['plan']

# SIDEBAR
# with st.sidebar:
#     if 'plan' in st.session_state:
#         save_button = st.button("Save Plan",on_click=utils.ui_functions.save_plan,key='save')

utils.ui_functions.make_sidebar()

st.header('Future Events')
utils.ui_functions.add_colorful_divider()

col1, col2 = st.columns(2)

with col1:
    st.button(f"{BUTTON_BUY_HOME} Buy Home",
              on_click=add_new_home,
              args=[st.session_state],
              use_container_width=True)
    st.button(f"{BUTTON_BUY_CAR} Buy Car",
              on_click=add_new_car,
              args=[st.session_state],
              use_container_width=True)
with col2:
    # Have Child
    st.button(f"{BUTTON_HAVE_CHILD} Have Child",on_click=add_child,use_container_width=True)
    # Combine Expenses (disable only if none combinable AND no event exists)
    combinable = utils.generators_ui.get_combinable_expense_names(st.session_state['plan'])
    has_combine_event = any(ev[1]=='Combine Expenses' for ev in st.session_state['plan'].events)
    st.button(
        f"{BUTTON_COMBINE_EXPENSES} Combine Expenses",
        on_click=lambda: add_combine_expenses(st.session_state),
        disabled=(len(combinable)==0 and not has_combine_event),
        use_container_width=True
    )
    # Marriage (enabled only if not already married in any year)
    can_set_marriage = (not any(st.session_state['plan'].married))
    st.button(f"{BUTTON_GET_MARRIED} Get Married", on_click=lambda: add_marriage_event(st.session_state), disabled=(not can_set_marriage), use_container_width=True)

@st.dialog('Get Married')
def add_marriage_event(session_state):
    plan = session_state['plan']
    savings_assets = [obj for obj in plan.assets if obj.subcategory == 'Savings']
    with st.form("marriage_event_form"):
        year = st.number_input(
            "Marriage Year",
            min_value=plan.start_year,
            max_value=plan.start_year + plan.n_years,
            value=plan.start_year,
            step=1,
            key="marriage_event_year",
        )
        budget = st.number_input(
            "Wedding Budget",
            min_value=0,
            value=0,
            step=100,
            key="marriage_event_budget",
        )
        st.text('Budget Sources (proportions sum to 1.0)')
        df = pd.DataFrame(
            [
                (obj.id, obj.name, (plan.get_object_from_id(obj.person).name if obj.person != 'Joint' else 'Joint'), None)
                for obj in savings_assets
            ],
            columns=['id','Name','Person','Proportion']
        )
        sources_df = st.data_editor(
            df,
            column_config={'id':None},
            disabled=['Name','Person'],
            hide_index=True,
            key='marriage_sources_editor'
        )
        submit = st.form_submit_button("Add Marriage Event")
    if submit:
        # Extract proportions
        sources = []
        for i in range(len(sources_df)):
            prop = sources_df.loc[i, 'Proportion']
            if prop is not None and prop != 0:
                sources.append((sources_df.loc[i,'id'], float(prop)))
        utils.generators_ui.marriage_create_event(st.session_state, year, budget, sources)
        st.rerun()

# Generate Objects

for triple in sorted(st.session_state['plan'].events, key=lambda x: x[0]):
    if triple[1] in ['Buy Home','Buy Car']:
        utils.generators_ui.generate_asset(triple[2],st.session_state)
    elif triple[1] == 'Have Child':
        utils.generators_ui.generate_child(triple[2], st.session_state)
    elif triple[1] == 'Combine Expenses':
        utils.generators_ui.generate_combine_expenses(triple, st.session_state)
    elif triple[1] == 'Get Married':
        utils.generators_ui.generate_marriage_event(triple, st.session_state)
        
        # # Combine Expenses
        # st.session_state['expense_list'] = list(set([obj.name for obj in st.session_state['plan'].expenses if obj.person != 'Joint']))
        
        # st.checkbox('Combined Expenses',value=st.session_state['plan'].combined_expenses,
        #             on_change=update_combine,
        #             #args=['combined_expenses'],
        #             key='plan_combined_expenses')
        # if st.session_state['plan'].combined_expenses==False:
        #     st.number_input('Combine Year',
        #                     min_value=st.session_state['plan_start_year'],
        #                     max_value = (st.session_state['plan_start_year']+st.session_state['plan_n_years']),
        #                     value=st.session_state['plan'].combine_year,
        #                     step=1,
        #                     on_change=update_combine,
        #                     args=[st.session_state['expense_list']],
        #                     key='plan_combine_year')



