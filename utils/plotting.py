################################
# PLOTTING AND TABLE FUNCTIONS #
################################

import pandas as pd
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import json


import objs.financial_objects 
import objs.plan
import utils.utilities

ratio_rec_file_path = 'data/ratio_recommendations.json'

with open(ratio_rec_file_path, 'r') as j:
    try:
        ratio_rec_dict = json.loads(j.read())
    except json.decoder.JSONDecodeError as e:
        print(f"Invalid JSON string: {e}")

# Shared palette for cash flow-related visuals
CASHFLOW_COLORS = {
    'Income':'#9467bd',
    'Necessary':'#0077cc',
    'Discretionary':'#f4b000',
    'Savings':'#2ca02c',
    'Tax':'#d62728'
}

def make_people_list(plan,people):
    if people == 'Joint':
        people = [person.id for person in plan.people if person.dependent == False]
    else:
        people = [people]
    return(people)

def to_dataframe(plan,people,category,incl_tax_keyword=False):
    people = people + ['Joint'] #make_people_list(plan,people)
   # print(people)
    all_out = []
    
    if incl_tax_keyword == True:
        tax_keyword = ['tax_keyword']
    else:
        tax_keyword = []
    #print(people)
    for item in [x for x in getattr(plan,category) if x.person in people]:
        if item.person == 'Joint':
            for person in [x for x in item.components.keys() if x in people]:
                temp = pd.DataFrame(
                        {key:item.__dict__[key] for key in ['id','category','subcategory','name']+tax_keyword}|{'person':person,'value':item.components[person]},index=item.cal_year
                    ).reset_index(
                        drop=False
                    ).rename(
                        columns={'index':'cal_year','person':'person_split'}
                    )
                temp['person'] = 'Joint'
                all_out.append(temp)
        else:
            temp = pd.DataFrame(
                {key:item.__dict__[key] for key in ['id','person','category','subcategory','name','value']+tax_keyword},index=item.cal_year
                ).reset_index(
                    drop=False
                ).rename(
                    columns={'index':'cal_year','person':'person_split'}
                )
            temp['person'] = temp['person_split']
            all_out.append(temp)
    if len(all_out) == 0:
        df = pd.DataFrame({'cal_year':plan.cal_year,'id':'','person_split':'','category':'','subcategory':'','name':'','value':0,'person':''})
    else:
        df = pd.concat(all_out)
    return(df)

def generate_statement(plan,people,year,statement_type='cashflow'):
    if statement_type == 'cashflow':
        obj_type_list = ['Income','Expense']
        obj_type_ext = ['income','expenses']
    elif statement_type=='balance_sheet':
        obj_type_list = ['Asset','Liability']
        obj_type_ext = ['assets','liabilities']
    people = make_people_list(plan, people) 
    
    A_df = to_dataframe(plan, people, obj_type_ext[0])    
    if statement_type == 'cashflow':
        A_df = A_df.loc[(A_df['subcategory']!='Employer Match')&(A_df['cal_year']==year)&(A_df['value']>0.0),:]
    elif statement_type == 'balance_sheet':
        A_df = A_df.loc[(A_df['cal_year']==year)&(A_df['value']>0.0),:]
    A_df['obj_type'] = obj_type_list[0]
    if len(people) > 1:
        A_df['name'] += A_df['person'].apply(lambda x: '' if x == 'Joint' else ' ('+plan.get_object_from_id(x).name+')')
    #
    B_df = to_dataframe(plan, people, obj_type_ext[1])
    B_df = B_df.loc[(B_df['cal_year']==year)&(B_df['value']>0.0),:]

    if statement_type == 'cashflow':
        B_df.sort_values(by="category", key=lambda column: column.map(lambda e: ['Tax','Necessary','Discretionary','Savings'].index(e)), inplace=True)
    B_df['obj_type'] = obj_type_list[1]
    #
    df = pd.concat([A_df,B_df])
    
    #
    if statement_type == 'cashflow':
        sorter = list(A_df['category'].unique()) + ['Tax','Necessary','Discretionary','Savings']
    elif statement_type == 'balance_sheet':
        sorter = list(A_df['category'].unique()) + list(B_df['category'].unique())
    #
    df_cat = df.loc[:,['obj_type','category','value']].groupby(['obj_type','category']).sum().reset_index(drop=False)    
    df_cat.sort_values(by="category", key=lambda column: column.map(lambda e: sorter.index(e)), inplace=True)
    df_subcat = df.loc[:,['obj_type','category','subcategory','value']].groupby(['obj_type','category','subcategory']).sum().reset_index(drop=False).sort_values(by='value',ascending=False)
    df_name = df.loc[:,['obj_type','category','subcategory','name','value']].groupby(['obj_type','category','subcategory','name']).sum().reset_index(drop=False).sort_values(by='value',ascending=False)
    out_df = pd.DataFrame({'obj_type':pd.Series(dtype='object'),
                           'category':pd.Series(dtype='object'),
                           'subcategory':pd.Series(dtype='object'),
                           'name':pd.Series(dtype='object'),
                           'value':pd.Series(dtype='int')})

    for obj_type in obj_type_list:
        out_df = pd.concat([out_df,pd.DataFrame({'obj_type':[obj_type]})])
        for cat in df_cat.loc[df_cat['obj_type']==obj_type,'category']:
            cat_value = df_cat.loc[(df_cat['obj_type']==obj_type) & (df_cat['category']==cat),'value'].sum()
            out_df = pd.concat([out_df,pd.DataFrame({'category':[cat],'value':[str(cat_value)]})])
            for subcat in df_subcat.loc[(df_subcat['obj_type']==obj_type)&(df_subcat['category']==cat),'subcategory']:
                out_df = pd.concat([out_df,pd.DataFrame({'subcategory':[subcat],'value':['']})]) #df_subcat.loc[df_subcat['subcategory']==subcat,'value']})])
                for name in df_name.loc[(df_name['obj_type']==obj_type)&(df_name['category']==cat)&(df_name['subcategory']==subcat),'name']:
                    name_value = df_name.loc[(df_name['obj_type']==obj_type) &
                                             (df_name['category']==cat) &
                                             (df_name['subcategory']==subcat) &
                                             (df_name['name']==name),'value'].sum()
                    out_df = pd.concat([out_df,pd.DataFrame({'name':[name],'value':[str(name_value)]})])
    if statement_type == 'balance_sheet':
        out_df = pd.concat([out_df,pd.DataFrame({'obj_type':['Net Worth'],'value':[str(A_df['value'].sum()-B_df['value'].sum())]})])
    
    out_df = out_df.fillna('').reset_index(drop=True)
    return(out_df)

def expense_plots(plan,people,level,after_tax=False):
    joint_view = (people == 'Joint')
    if joint_view:
        people = [person.id for person in plan.people if person.dependent == False] + ['Joint']
        rows = []
        for item in plan.expenses:
            if item.person == 'Joint':
                temp = pd.DataFrame(
                    {key:item.__dict__[key] for key in ['id','category','subcategory','name','value']},
                    index=item.cal_year
                ).reset_index(drop=False).rename(columns={'index':'cal_year'})
                temp['person_split'] = 'Joint'
                rows.append(temp)
            else:
                temp = pd.DataFrame(
                    {key:item.__dict__[key] for key in ['id','person','category','subcategory','name','value']},
                    index=item.cal_year
                ).reset_index(drop=False).rename(columns={'index':'cal_year','person':'person_split'})
                rows.append(temp)
        if len(rows) == 0:
            df = pd.DataFrame({'cal_year':plan.cal_year,'person_split':'','category':'','subcategory':'','name':'','value':0})
        else:
            df = pd.concat(rows)
    else:
        people = make_people_list(plan,people)
        df = to_dataframe(plan, people, 'expenses')

    if level == 'category':
        level_list = ['category']
    elif level == 'subcategory':
        level_list = ['category','subcategory']
    elif level == 'name':
        level_list = ['category','subcategory','name']    

    
    exp_grouped = df.loc[df['person_split'].isin(people),level_list+['cal_year','value']].groupby(level_list+['cal_year'],as_index=False).sum(numeric_only=None)
    if level == 'name':
        exp_grouped['line_key'] = exp_grouped['category'].astype(str) + '|' + exp_grouped['subcategory'].astype(str) + '|' + exp_grouped['name'].astype(str)
    after_tax_exp_grouped = exp_grouped.loc[exp_grouped['category']!='Tax',:] #.groupby(['category','subcategory','owner','cal_year'],as_index=False).sum(numeric_only=None)
    
    col_dict = CASHFLOW_COLORS
    
    if after_tax == False:
        fig = px.area(exp_grouped, 
                      x="cal_year", 
                      y="value", 
                      color='category', 
                      line_group='line_key' if level == 'name' else level, 
                      #title="All Expenses",
                      color_discrete_map=col_dict,
                      template='seaborn')
    else:
        fig = px.area(after_tax_exp_grouped,
                       x="cal_year",
                       y="value",
                       color='category',
                       line_group='line_key' if level == 'name' else level,
                       #title="After Tax Expenses",
                       groupnorm='percent',
                       color_discrete_map=col_dict,
                       template='seaborn')
    # Add income overlay for context
    income_people = [person.id for person in plan.people if person.dependent == False] if joint_view else people
    income_df = to_dataframe(plan, income_people, 'income')
    income_df = income_df.loc[income_df['subcategory']!='Employer Match',:]
    income_series = income_df.loc[income_df['person_split'].isin(income_people),['cal_year','value']].groupby('cal_year').sum(numeric_only=True)['value']
    fig.add_traces(go.Scatter(x=income_series.index,
                              y=income_series.values,
                              name='Income',
                              line=dict(color='#222222', dash='dash'),
                              mode='lines'))
    return({'df':exp_grouped,'fig':fig})


def asset_plots(plan,people,level,net_worth_formula=2):
    people = make_people_list(plan,people)
    
    if level == 'category':
        level_list = ['category']
    elif level == 'subcategory':
        level_list = ['category','subcategory']
    elif level == 'name':
        level_list = ['category','subcategory','name']  
        
    #
    asset_df = to_dataframe(plan,people,'assets')
    liab_df = to_dataframe(plan,people,'liabilities')
    liab_df['value'] = -liab_df['value']
    total_df = pd.concat([asset_df,liab_df])
    #
    total_grouped = total_df.loc[total_df['person_split'].isin(people),level_list+['cal_year','value']].groupby(level_list+['cal_year'],as_index=False).sum(numeric_only=None)
    
    # For Net Worth/FIRE Benchmarks
    inc_df = to_dataframe(plan, people, 'income')
    inc_df = inc_df.loc[inc_df['subcategory']!= 'Employer Match',:]
    exp_df = to_dataframe(plan, people, 'expenses')
    exp_df = exp_df.loc[exp_df['category'].isin(['Necessary','Discretionary']),:]
      
    # PLOT 1 - NET WORTH
    net_worth = total_grouped.loc[:,['cal_year','value']].groupby(['cal_year']).sum(numeric_only=None)
    net_worth.index.names = [None]    
    
    age = sum([plan.get_object_from_id(person).age for person in people])/len(people)
    
    # Target Net Worth
    gross_income = inc_df.groupby('cal_year').sum(numeric_only=True)['value']
    retirement_age = 65
    
    if net_worth_formula == 1:
        target_net_worth = age * gross_income / 10
    elif net_worth_formula == 2:
        target_net_worth = 10 * (age/retirement_age) * gross_income
      
    fig1 = px.bar(total_grouped, 
                 x="cal_year", 
                 y="value", 
                 color=level,
                 template='seaborn')
    
    fig1.add_traces(go.Scatter(x=net_worth.index,
                               y=net_worth['value'], 
                               name = 'Net Worth',
                               marker = {'color':'black'},
                               #line = {'dash':'solid'},
                               mode = 'lines'))
    
    fig1.add_traces(go.Scatter(x=target_net_worth.index,
                              y=target_net_worth,
                              name = 'Net Worth Goal',
                              marker = {'color':'black'},
                              line={'dash':'dot'},
                              mode = 'lines'))
      
    #PLOT 2 - RETIREMENT ACCOUNTS
      
    # 2. Fire Number = 25 * annual expenses
    fire_number = 25*exp_df.loc[:,['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
      
    fig2 = px.bar(total_df.loc[total_df['subcategory']=='Retirement',:], 
                  x="cal_year", 
                  y="value", 
                  color="name", 
                  #title="Retirement Accounts",
                  #color_discrete_sequence=px.colors.qualitative.T10,
                  template='seaborn')
    
    fig2.add_traces(go.Scatter(x=fire_number.index,
                              y=fire_number['value'],
                              name = 'FIRE Number',
                              marker = {'color':'black'},
                              line={'dash':'dot'},
                              mode = 'lines'))
      
    return({'fig1':fig1,'fig2':fig2})


def cashflow_sankey(plan,people,year,comb_all_exp=False,normalize=False):
    # Never forget - though this visualization may seem "extra", it will
    # expose any flaws in the balancing process
    
    joint_view = (people == 'Joint')
    people = make_people_list(plan,people)
    tax_filing = plan.tax_df['filing_status'].loc[year]
    if isinstance(tax_filing,pd.Series):
        tax_filing = tax_filing.unique()[0]
    
    joint_rollup = joint_view and (tax_filing == 'joint')
    label_people = ['Joint'] if joint_rollup else people
    if comb_all_exp == True:
        label_dict = {person:{'Savings':'Savings',
                              'Necessary':'Necessary',
                              'Discretionary':'Discretionary'} for person in label_people}
    else:
        label_dict = {person:{'Savings':'Savings' if person == 'Joint' else 'Savings ('+plan.get_object_from_id(person).name+')',
                              'Necessary':'Necessary' if person == 'Joint' else 'Necessary ('+plan.get_object_from_id(person).name+')',
                              'Discretionary':'Discretionary' if person == 'Joint' else 'Discretionary ('+plan.get_object_from_id(person).name+')'} for person in label_people}
    
    if tax_filing == 'joint':
        label_dict = {person:(label_dict[person]|{'Tax':'Tax',
                                                  'Taxable Income':'Taxable Income'}) for person in label_dict.keys()}
    else:
        label_dict = {person:(label_dict[person]|{'Tax':'Tax ('+plan.get_object_from_id(person).name+')',
                                                  'Taxable Income':'Taxable Income ('+plan.get_object_from_id(person).name+')'}) for person in label_dict.keys()}

    # Make data frames and subset
    inc_df = to_dataframe(plan,people,'income')#,split_joint=False)
    inc = inc_df.loc[(inc_df['cal_year']==year)&(inc_df['value']>0.0)].reset_index(drop=True)
    #
    tot = inc['value'].sum()
    #
    exp_df = to_dataframe(plan,people,'expenses',incl_tax_keyword=True)
    exp = exp_df.loc[(exp_df['cal_year']==year)&(exp_df['value']>0.0)].reset_index(drop=True)

    if joint_rollup:
        inc['person_split'] = 'Joint'
        inc['person'] = 'Joint'
        exp['person_split'] = 'Joint'
        exp['person'] = 'Joint'

    # Pull employer match and add to expenses:
    # match_to_add = inc.loc[inc['subcategory']=='Employer Match',:].reset_index(drop=True)
    # match_to_add.loc[:,['category','subcategory','tax_keyword']] = exp.loc[exp['tax_keyword']=='401k',['category','subcategory','tax_keyword']].reset_index(drop=True)
    # exp = pd.concat([exp,match_to_add]).reset_index(drop=True)
    
    # Get person names instead of ID for non-joint expenses, etc..
    inc.loc[inc['person_split']!='Joint','name'] = inc.loc[inc['person_split']!='Joint','subcategory'] + ' ('+inc.loc[inc['person_split']!='Joint','person_split'].apply(lambda x: plan.get_object_from_id(x).name)+')'
    
    if comb_all_exp == False:
        exp.loc[(exp['person']!='Joint')&(exp['category']!='Tax'),'category'] += ' ('+exp.loc[(exp['person']!='Joint')&(exp['category']!='Tax'),'person'].apply(lambda x: plan.get_object_from_id(x).name)+')'
        exp.loc[exp['person']!='Joint','subcategory'] += ' ('+exp.loc[exp['person']!='Joint','person'].apply(lambda x: plan.get_object_from_id(x).name)+')'
        exp.loc[exp['person']!='Joint','name'] += ' ('+exp.loc[exp['person']!='Joint','person'].apply(lambda x: plan.get_object_from_id(x).name)+')'
    
    if tax_filing != "joint":
        exp.loc[(exp['person']!='Joint')&(exp['category']=='Tax'),'category'] += ' ('+exp.loc[(exp['person']!='Joint')&(exp['category']=='Tax'),'person'].apply(lambda x: plan.get_object_from_id(x).name)+')'

    
    # Add Child Expenses to names
    exp.loc[exp['subcategory']=='Child','name'] = exp['name'] +' (Child)'
    
    # Preallocate
    nodes = []
    node_color = []

    # Income
    income = inc.loc[inc['subcategory']!='Employer Match',['person_split','name','value']].rename(columns={'name':'source','person_split':'person'})
    income = income.merge(pd.DataFrame({'person':label_dict.keys(),'target':[label_dict[person]['Taxable Income'] for person in label_dict.keys()]}))
    nodes += list(income['source'].unique())
    node_color += ['Income' for _ in income['source'].unique()]
    
    # Employer Match
    # employer_match_ = inc.loc[inc['subcategory']=='Employer Match',['person','name','value']].rename(columns={'name':'source'})
    # employer_match_ = employer_match_.merge(pd.DataFrame({'person':label_dict.keys(),'target':[label_dict[person]['Savings'] for person in label_dict.keys()]}))
    # nodes += list(employer_match_['source'].unique())
    # node_color += ['Income' for _ in employer_match_['source'].unique()]
    # print(employer_match_)
    
    # Tax-exempt Savings
    pretax_mask = exp['tax_keyword'].fillna('').isin(['Traditional','HSA']) & (exp['id'].apply(lambda x: x.split('_')[0]) != 'Income')
    pretax = exp.loc[pretax_mask,['person_split','name','value']].rename(columns={'name':'target','person_split':'person'})
    pretax_grouped = pretax.loc[:,['person','value']].groupby('person').sum().reset_index(drop=False)
    pretax_grouped = pretax_grouped.merge(income[['person','source']],on='person')
    pretax_grouped = pretax_grouped.merge(pd.DataFrame({'person':label_dict.keys(),'target':[label_dict[person]['Savings'] for person in label_dict.keys()]}))
    #
    for person in pretax_grouped['person'].unique():
        income.loc[income.index==income.loc[(income['person']==person),'value'].idxmax(),'value'] -= pretax_grouped.loc[pretax_grouped['person']==person,'value']   
        
    # Expense Categories
    posttax_cat = exp.loc[~pretax_mask,['person_split','category','value']].groupby(['person_split','category']).sum().reset_index(drop=False).rename(columns={'category':'target'})
    posttax_cat = posttax_cat.merge(pd.DataFrame({'person':label_dict.keys(),'source':[label_dict[person]['Taxable Income'] for person in label_dict.keys()]}),left_on='person_split',right_on='person')
        
    #
    nodes += list(posttax_cat['source'].unique())
    node_color += ['Income' for _ in posttax_cat['source'].unique()]
    nodes += list(posttax_cat['target'].unique())
    node_color += [x.split(' ')[0] for x in posttax_cat['target'].unique()]
    #
    cat_conversion = {key:i for key, i in zip(nodes,list(range(len(nodes))))}
    links = pd.concat([income[['source','target','value']],
                      # employer_match_[['source','target','value']],
                      pretax_grouped[['source','target','value']],
                      posttax_cat[['source','target','value']]]).reset_index(drop=True)
    
    links['source'] = links['source'].map(lambda x: cat_conversion.get(x, x))
    links['target'] = links['target'].map(lambda x: cat_conversion.get(x, x))
    
    # Subcategories
    posttax_subcat = exp.loc[:,['person_split','category','subcategory','value']].groupby(['person_split','category','subcategory']).sum().reset_index(drop=False).rename(columns={'category':'source','subcategory':'target'})
    posttax_subcat.loc[:,'color_cat'] = posttax_subcat['source'].apply(lambda x: x.split(' ')[0])
    #
    subcat_pairs_cat,subcat_pairs_node = zip(*list(set([(posttax_subcat.loc[i,'color_cat'],posttax_subcat.loc[i,'target']) for i in posttax_subcat.index])))
    nodes += list(subcat_pairs_node)
    node_color += list(subcat_pairs_cat)
    #
    subcat_conversion = {key:(i+len(cat_conversion)) for key,i in zip(subcat_pairs_node,list(range(len(subcat_pairs_node))))}
    links = pd.concat([links,
                      posttax_subcat[['source','target','value']]]).reset_index(drop=True)
    
    links['source'] = links['source'].map(lambda x: cat_conversion.get(x, x))
    links['target'] = links['target'].map(lambda x: subcat_conversion.get(x, x))
    
    # Names
    posttax_name = exp.loc[:,['person_split','subcategory','name','value']].groupby(['person_split','subcategory','name']).sum().reset_index(drop=False).rename(columns={'subcategory':'source','name':'target'})
    posttax_name = posttax_name.merge(posttax_subcat.rename(columns={'target':'temp'})[['color_cat','temp']].drop_duplicates(),left_on='source',right_on='temp')
    #
    name_pairs_cat,name_pairs_node = zip(*list(set([(posttax_name.loc[i,'color_cat'],posttax_name.loc[i,'target']) for i in posttax_name.index])))
    nodes += list(name_pairs_node)
    node_color += list(name_pairs_cat)    
    #
    name_conversion = {key:(i+len(subcat_conversion)+len(cat_conversion)) for key,i in zip(name_pairs_node,list(range(len(name_pairs_node))))}                   
    links = pd.concat([links,
                      posttax_name[['source','target','value']]
                      ]).reset_index(drop=True)
    
    links['source'] = links['source'].map(lambda x: subcat_conversion.get(x, x))
    links['target'] = links['target'].map(lambda x: name_conversion.get(x, x))
    
    # Colors
    node_color = [CASHFLOW_COLORS[cat] for cat in node_color]

    if normalize == True:
        links['value'] = (100*links['value']/tot)
        links['value'] = links['value'].round(1)
    else:
        links['value'] = links['value'].round(0)
    fig = go.Figure(data=[go.Sankey(
            arrangement='snap',
            node = dict(
                pad = 10,
                thickness = 20,
                line = dict(color = 'rgba(0,0,0,0.25)', width = 0.5),
                label = nodes,
                color = node_color
                ),
            link = dict(
                source = links['source'],
                target = links['target'],
                value = links['value'])
            )])

    # Improve label readability: use a high-contrast font color and consistent size
    fig.update_traces(textfont=dict(color='white', size=12))

    return(fig)

# https://stackoverflow.com/questions/72749062/how-to-set-order-of-the-nodes-in-sankey-diagram-plotly
# Deal with withdrawing from savings for expenses

##### ANALYTICAL TIME SERIES

def compute_analytical_timeseries(plan,people):
    people = make_people_list(plan,people)

    asset_df = to_dataframe(plan,people,'assets')
    liab_df = to_dataframe(plan,people,'liabilities')
    inc_df = to_dataframe(plan, people, 'income')
    exp_df = to_dataframe(plan, people, 'expenses')
        
    gross_income = inc_df.loc[inc_df['subcategory']!='Employer Match',['cal_year','value']].groupby('cal_year').sum(numeric_only=True)
    income_tax = exp_df.loc[(exp_df['category']=='Tax')&(exp_df['subcategory']=='Income'),['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    after_tax_income  = gross_income-income_tax
    
    ### Savings and Liquidity Metrics
    
    # 1. Liquidity Ratio = cash and cash investments / (non-discretionary expenses/12) (monthly)
    # 3 to 6 (i.e. months of emergency fund)
    
    cash_assets = asset_df.loc[asset_df['subcategory'].isin(['Savings','Bonds']),['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    non_discretionary_expenses = exp_df.loc[exp_df['category']=='Necessary',['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    
    liquidity_ratio = cash_assets/(non_discretionary_expenses/12)
    
    # 2. Savings Ratio =  cash savings / after-tax income
    # Around 10% ? That seems crazy
    
    cash_savings = exp_df.loc[exp_df['subcategory']=='Savings',['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    
    after_tax_savings_ratio = cash_savings/after_tax_income
    
    # 3. Total Savings Ratio =  savings + employer match / gross income
    # Depends on retirement needs
    
    retirement_savings = exp_df.loc[exp_df['subcategory']=='Retirement',['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    total_savings = cash_savings + retirement_savings
    
    total_savings_ratio = total_savings/gross_income
    
    # 4. Current Ratio = cash assets / current liabilities
    # Short term debt...I don't really plan to carry short-term debt at the moment
    # Can approximate by total annual debt payments
    # Want greater than one, for sure
    
    current_liabilities = exp_df.loc[exp_df['subcategory'].str.split(' ').apply(lambda x:'Loan' in x)|(exp_df['name']=='Mortgage'),['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    
    current_ratio = cash_assets/current_liabilities
    
    ### Debt Metrics
    
    # 1. Debt to Assets: total liabilities / total assets
    # Decrease over time, between 0.3 and 0.6
    
    total_liabilities = liab_df.loc[:,['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    total_assets = asset_df.loc[:,['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    
    debt_to_asset_ratio = total_liabilities/total_assets
    
    # 2. Debt-to-Income Ratio: total debt payments (or current liabilities?) / gross income
    # Keep below 35%
    
    debt_to_income_ratio = current_liabilities/gross_income
    
    # 3. Non-Mortgage-Debt-Service Ratio: (total debt payments - mortgage payment) / gross income
    # Keep below 15%
    
    non_mortgage_debt_service_ratio = (current_liabilities - exp_df.loc[exp_df['name']=='Mortgage',['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True))/gross_income
    
    # 4. Household-Debt-Service Ratio: (total debt payments-mortgage payment)/ after-tax income
    # Keep below 25%
    
    household_debt_service_ratio = (current_liabilities - exp_df.loc[exp_df['name']=='Mortgage',['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True))/after_tax_income
    
    # 5. Cost of Debt: Sum_i (balance_i*rate_i) / total debt
    # Below average rate of return on investments..
    
    #This will require a little more work, since I need rates...will have to pull from liab_objects
    
    ### Net Worth, Investments, and Solvency Metrics
    
    net_worth = total_assets - total_liabilities #pd.concat([asset_df,liab_df.apply()]).loc[:,['cal_year','value']].groupby(['cal_year']).sum(numeric_only=True)
    
    # Plotted Above
    # # 1. Target Net Worth = Age * gross income / 10
    # # Compare to Net Worth
    
    # ages = pd.Series([age+i for i in range(len(years))])
    # target_net_worth = age * gross_income / 10
    
    # # 2. Fire Number = 25 * annual expenses
    # # Compare to Retirement Savings
    
    # fire_number = 25*exp_df.loc[exp_df['category'].isin(['Discretionary','Necessary'])].groupby(['cal_year']).sum(numeric_only=True)
    
    # 3. Liquid Savings to Net Worth = cash savings / net worth
    # Shoot for 15% ?
    
    liquid_savings_to_net_worth_ratio = cash_assets/net_worth
    
    # 4. Invested Assets to Net Worth = invested assets / net worth
    # Trend higher over time...? 50% or more
    
    invested_assets = asset_df.loc[asset_df['category']=='Investment',['cal_year','value']].groupby('cal_year').sum(numeric_only=True)
    
    invested_assets_to_net_worth_ratio = invested_assets/net_worth
    
    # 5. Solvency Ratio: net worth / total assets
    # 0.2 when young, approach 0.9 in retirement
    
    solvency_ratio = net_worth/total_assets
    
    # 6. Basic Housing Ratio: housing costs / gross income
    # Less than 0.28, or 0.33 in HCOL
    
    housing_costs = exp_df.loc[(exp_df['subcategory'].isin(['Home','Utilities']))|(exp_df['name']=='Property Tax'),['cal_year','value']].groupby('cal_year').sum(numeric_only=True)
    
    basic_housing_ratio = housing_costs/gross_income
    
    # 7. Investment Assets to Gross Pay: invested assets + cash / gross income
    # Goal: 20:1 by retirement
    
    investment_assets_to_gross_pay_ratio = (invested_assets + cash_assets)/gross_income
    
    output_dict = {'gross_income':gross_income,
        'after_tax_income':after_tax_income,
        'cash_assets':cash_assets,
        'non_discretionary_expenses':non_discretionary_expenses,
        'liquidity_ratio':liquidity_ratio,
        'cash_savings':cash_savings,
        'after_tax_savings_ratio':after_tax_savings_ratio,
        'retirement_savings':retirement_savings,
        'total_savings':total_savings,
        'total_savings_ratio':total_savings_ratio,
        'current_liabilities':current_liabilities,
        'current_ratio':current_ratio,
        'total_liabilities':total_liabilities,
        'total_assets':total_assets,
        'debt_to_asset_ratio':debt_to_asset_ratio,
        'debt_to_income_ratio':debt_to_income_ratio,
        'non_mortgage_debt_service_ratio':non_mortgage_debt_service_ratio,
        'household_debt_service_ratio':household_debt_service_ratio,
        'net_worth':net_worth,
        'liquid_savings_to_net_worth_ratio':liquid_savings_to_net_worth_ratio,
        'invested_assets':invested_assets,
        'invested_assets_to_net_worth_ratio':invested_assets_to_net_worth_ratio,
        'solvency_ratio':solvency_ratio,
        'housing_costs':housing_costs,
        'basic_housing_ratio':basic_housing_ratio,
        'investment_assets_to_gross_pay_ratio':investment_assets_to_gross_pay_ratio}
    
    output_df = pd.DataFrame({key:value.squeeze() for key, value in output_dict.items()})

    return(output_df)

# ratio_rec_dict = {
#     'liquidity_ratio':{'name':'Liquidity Ratio','ymin':6,'ymax':6,'n':6,'marker':'triangle-up'},
#     'after_tax_savings_ratio':{'name':'After Tax Savings Ratio','ymin':0.1,'ymax':0.1,'n':6,'marker':'triangle-up'},
#     'total_savings_ratio':{'name':'Total Savings Ratio','ymin':0.2,'ymax':0.2,'n':6,'marker':'triangle-up'},
#     'current_ratio':{'name':'Current Ratio','ymin':1,'ymax':1,'n':6,'marker':'triangle-up'},
#     'debt_to_asset_ratio':{'name':'Debt to Asset Ratio','ymin':0.5,'ymax':0.5,'n':6,'marker':'triangle-down'},
#     'debt_to_income_ratio':{'name':'Debt to Income Ratio','ymin':0.35,'ymax':0.35,'n':6,'marker':'triangle-down'},
#     'non_mortgage_debt_service_ratio':{'name':'Non-Mortgage Debt Ratio','ymin':0.15,'ymax':0.15,'n':6,'marker':'triangle-down'},
#     'household_debt_service_ratio':{'name':'Household Debt Service Ratio','ymin':0.25,'ymax':0.25,'n':6,'marker':'triangle-down'},
#     'liquid_savings_to_net_worth_ratio':{'name':'Liquid Savings to Net Worth Ratio','ymin':0.15,'ymax':0.15,'n':6,'marker':'triangle-up'},
#     'invested_assets_to_net_worth_ratio':{'name':'Invested Assets to Net Worth Ratio','ymin':0.5,'ymax':0.5,'n':6,'marker':'triangle-up'},
#     'solvency_ratio':{'name':'Solvency Ratio','ymin':0.2,'ymax':0.9,'n':6,'marker':'triangle-up'},
#     'basic_housing_ratio':{'name':'Basic Housing Ratio','ymin':0.33,'ymax':0.33,'n':6,'marker':'triangle-up'},
#     'investment_assets_to_gross_pay_ratio':{'name':'Investment Assets to Gross Pay Ratio','ymin':1.5,'ymax':20,'n':6,'marker':'triangle-up'}
#     }

def arrow_line(xmin,xmax,ymin,ymax,n):
  xlist = [xmin+(xmax-xmin)*i/(n-1) for i in range(n)]
  ylist = [ymin+(ymax-ymin)*i/(n-1) for i in range(n)]
  return([xlist,ylist])

def ratio_plot(df,names): #,rec_dict):
    if isinstance(names,str):
        names = [names]
    
    fig = go.Figure() #template='seaborn')
    
    for name_ in names:
        ratio = df[name_]
    
        fig.add_trace(go.Scatter(
            x=ratio.index,
            y=ratio,
            mode='lines+markers',
            name=ratio_rec_dict[name_]['name'],
            line=dict(
                width=3,
                color=px.colors.qualitative.G10[list(ratio_rec_dict.keys()).index(name_) % 10],
                ),
            marker=dict(
                size=10
                )
        ))
        
        arrows = arrow_line(min(ratio.index),max(ratio.index),
                            ratio_rec_dict[name_]['ymin'],ratio_rec_dict[name_]['ymax'],
                            ratio_rec_dict[name_]['n'])
        
        fig.add_trace(go.Scatter(
            x=arrows[0],
            y=arrows[1],
            mode='lines+markers',
            line=dict(
                width=3,
                color=px.colors.qualitative.G10[list(ratio_rec_dict.keys()).index(name_) % 10],
                dash='dash'
                ),
            marker=dict(
                size=18,
                symbol=ratio_rec_dict[name_]['marker']
                ),
            showlegend=False
        ))
    
    fig.update_layout(
        legend=dict(orientation='h',
                    yanchor="bottom",
                    y=-0.1,
                    xanchor="center",
                    x=0.5),
        margin=dict(t=10,l=10,b=10,r=10)
    )
    return(fig)
