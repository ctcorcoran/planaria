######################
# SPECIAL GENERATORS #
######################

# These are the functions that deal with major 
# real asset purchases such as homes, cars, boats,
# etc...any asset that has been purchased with a liability,
# and thus any object in which one can have equity

# These generators will create an asset object that either
# appreciates or depreciates, and a liability object used
# to purchase the asset. Each of these assets will also
# contain an equity attribute that is

# Equity = Asset - Liability

# Assets can also be purchased with cash, in which case 
# the liability object won't be created - just a single withdrawal

# Also, Child generators...

import pandas as pd
import objs.financial_objects 
import objs.plan
import utils.utilities

# equity

# buy_asset_with_liability
# general function for the mechanics of purchasing an asset with a liability

def buy_asset_with_liability(plan,person,start_year,tax_keyword_dict,value,asset_dict,liab_dict,down_payment_sources,down_payment_source_pct=True):    
    asset_obj = objs.financial_objects.AssetObj(person,
                                                asset_dict['cat'],
                                                asset_dict['subcat'],
                                                asset_dict['name'],
                                                tax_keyword_dict['asset'],
                                                plan.cal_year,
                                                value,
                                                asset_dict['growth_rate'],
                                                0,
                                                False,
                                                True,
                                                {'start_year':start_year})
    # Mark as future event object if created for future purchase
    if start_year > plan.start_year:
        asset_obj.future_event = True
    
    # Determine if a liability needs to be created or not
    if down_payment_sources == None:
        if liab_dict['attributes']['payment'] > 0:
            create_liability = True
        else:
            create_liability = False
    else:
        if liab_dict['attributes']['down_pct'] == True:
            if liab_dict['attributes']['down_payment'] == 1.0:
                create_liability = False
            else:
                create_liability = True
        else:
            if liab_dict['attributes']['down_payment'] == value:
                create_liability = False
            else:
                create_liability = True
                
    # If so, create liability
    if create_liability == True:
        # Add down_payment_sources if new:
        if down_payment_sources is not None:
            liab_dict['attributes'] |= {'down_payment_sources':down_payment_sources}
        
        # If existing, need the present value of the liability
        if down_payment_sources == None:
            existing = True
            liab_value = liab_dict['attributes']['present_value']
        else:
            existing = False
            liab_value = value
        
        # Create liability object
        liab_obj = objs.financial_objects.LiabObj(person,
                                                  liab_dict['cat'],
                                                  liab_dict['subcat'],
                                                  liab_dict['name'],
                                                  tax_keyword_dict['liability'],
                                                  plan.cal_year,
                                                  liab_dict['interest_rate'],
                                                  liab_value,
                                                  existing,
                                                  True,
                                                  liab_dict['attributes']|{'start_year':start_year})
        # Mark as future event object if created for future purchase
        if start_year > plan.start_year:
            liab_obj.future_event = True
        
        # Make value - asset_value pair for equity calculations  
        liab_obj.dependent_objs = True
        liab_obj.paired_attr['series'] |= {asset_obj.id:[['value','asset_value',1.0]]}
        liab_obj.paired_attr['time'] |= {asset_obj.id:[['start_year','start_year',0]]}
        
        plan.pairs['series'].append([asset_obj.id,liab_obj.id,])
        plan.pairs['time'].append([asset_obj.id,liab_obj.id])
        
        # Add objects to plan
        plan.liabilities.append(liab_obj)
        plan.assets.append(asset_obj)
        
        # Project liab_obj, which triggers all to update
        plan = liab_obj.project(plan)
        
        # Make an liability payment expense object
        plan = liab_obj.make_expense_obj(plan)
    
    else:
        # Add asset object to plan
        plan.assets.append(asset_obj)
        
        # Project liab_obj, which triggers all to update
        plan = asset_obj.project(plan)

       
    # down_payment_sources should be a dict of asset_ids and either amounts or fractions
    # amounts should sum of the down_payment amt, fractions should sum to 1
    # assets_replaced must be processed first, so any sale  is applied before withdrawing
    # the down_payment
    
    if down_payment_sources is not None:
        # Add start_year, end_year pairs of replaced expenses (e.g. rent)
        for obj_id in asset_dict['expenses_replaced']:
            obj = plan.get_object_from_id(obj_id)
            obj.paired_attr['time'] |= {asset_obj.id:[['start_year','end_year',-1]]}
            plan.pairs['time'].append([asset_obj.id,obj_id])
        
        # Add start_year, end_year pairs of replaced assets (e.g. old car), and
        # sell the asset
        for obj_id in asset_dict['assets_replaced']:
            obj = plan.get_object_from_id(obj_id)
            obj.paired_attr['time'] |= {asset_obj.id:[['start_year','end_year',-1]]}
            plan.pairs['time'].append([asset_obj.id,obj_id])
            #
            plan = obj.sell(plan,asset_obj.start_year,prune=True) #Use prune
        
        # If asset is new, with draw funds used for down_payment (or purchase outright)
        # If bought outright, keep track of payment sources in asset
        if create_liability == False:
            asset_obj.down_payment_sources = down_payment_sources
            down_payment = value
        else:
            down_payment = liab_obj.down_payment
        for source, amt in down_payment_sources:
            if down_payment_source_pct == True:
                amt = int(float(amt)*down_payment)
            plan.get_object_from_id(source).withdrawal(amt,start_year)
        
    
    return([plan,asset_obj.id])

# Specialized asset purchase for mortgage

# buy_home

def buy_home(plan,person,start_year,value,asset_dict,liab_dict,down_payment_sources,home_params):
    asset_dict = asset_dict | {'cat':'Tangible','subcat':'Real Estate','name':'Home'}
    liab_dict = liab_dict | {'cat':'Installment','subcat':'Mortgage','name':'Mortgage'}
    plan, asset_id = buy_asset_with_liability(plan,person,start_year,{'asset':'','liability':'Mortgage'},value,asset_dict,liab_dict,down_payment_sources)
    
    # Maintenance (optional cap)
    plan = plan.get_object_from_id(asset_id).make_expense_obj(
        plan,
        'maintenance',
        home_params['maintenance_rate'],
        cap=home_params.get('maintenance_cap', None)
    )
    
    # Property Tax
    plan = plan.get_object_from_id(asset_id).make_expense_obj(plan,'tax',home_params['property_tax_rate'])
     
    # Homeowner's Insurance
    insurance = objs.financial_objects.ExpenseObj(person,
                                "Necessary",
                                plan.get_object_from_id(asset_id).name, #"Home",
                                plan.get_object_from_id(asset_id).name + ' Insurance',#"Home Insurance",
                                '',
                                plan.cal_year,
                                home_params['insurance'],
                                False,
                                True,
                                {'infl_rate':plan.infl_rate,})
    # Mark as future event object if created for future purchase
    if start_year > plan.start_year:
        insurance.future_event = True
    
    insurance.paired_attr['time'] |= {asset_id:[['start_year','start_year',0],['end_year','end_year',0]]}
    plan.pairs['time'].append([asset_id,insurance.id])
    plan.expenses.append(insurance)
    plan = insurance.project(plan)
    
    # Project the home asset, triggering updates of all dependents
    plan = plan.get_object_from_id(asset_id).project(plan)
    
    # Add home purchase to events
    if down_payment_sources != None:
        plan.events.append([start_year,'Buy Home',asset_id])
    
    return(plan)

# buy_car

def buy_car(plan,person,start_year,value,asset_dict,liab_dict,down_payment_sources,car_params):
    age = asset_dict['model_year']-start_year
    years_owned = max(plan.cal_year)-start_year + 1
    # depreciation_rate = []
    # for yr in range(years_owned):
    #     if age+yr == 0:
    #         depreciation_rate.append(0.2)
    #     elif (0 < age+yr) & (age+yr <= 10):
    #         depreciation_rate.append(0.15)
    #     else:
    #         depreciation_rate.append(0.1)
            
    depreciation_rate = [-0.15 if (0 < age+yr) and (age+yr <= 5) else (-0.2 if age+yr==0 else -0.1) for yr in range(years_owned)]
    depreciation_rate = pd.Series(depreciation_rate,index=plan.cal_year[plan.cal_year >= start_year])
    depreciation_rate = utils.utilities.expand_contract(depreciation_rate, plan.cal_year)    
    
    asset_dict = asset_dict | {'cat':'Tangible','subcat':'Automobile','growth_rate':depreciation_rate}
    liab_dict = liab_dict | {'cat':'Installment','subcat':'Auto Loan','name':'Auto Loan'}
    plan, asset_id = buy_asset_with_liability(plan,
                                              person,
                                              start_year,
                                              {'asset':'','liability':''},
                                              value,
                                              asset_dict,
                                              liab_dict,
                                              down_payment_sources)

    # Maintenance
    plan = plan.get_object_from_id(asset_id).make_expense_obj(plan,
                                                              'maintenance',
                                                              car_params['maintenance_rate'])
    
    # Auto Insurance
    insurance = objs.financial_objects.ExpenseObj(person,
                                "Necessary",
                                "Auto",
                                "Auto Insurance",
                                '',
                                plan.cal_year,
                                car_params['insurance'],
                                False,
                                False,
                                {'infl_rate':plan.infl_rate})
    # Mark as future event object if created for future purchase
    if start_year > plan.start_year:
        insurance.future_event = True
    insurance.paired_attr['time'] |= {asset_id:[['start_year','start_year',0],['end_year','end_year',0]]}
    plan.pairs['time'].append([asset_id,insurance.id])
    plan.expenses.append(insurance)
    plan = insurance.project(plan)
    
    # Project auto asset, to project all dependents
    plan = plan.get_object_from_id(asset_id).project(plan)
    
    # Add car purchase to events
    if down_payment_sources != None:
        plan.events.append([start_year,'Buy Car',asset_id])
    
    return(plan)

# buy_and_replace_cars


############
# CHILDREN #
############

def expand_child_costs(input_df):
    # Assume Highest Income Bracket.. For Now
    input_df = input_df.loc[input_df['Salary']==max(input_df['Salary']),]
    age_list = []
    vals_dict = {cat:[] for cat in input_df.columns if cat not in ['Age Group','Salary','Total']}
    for i in range(len(input_df['Age Group'].unique())):
        age_group = input_df['Age Group'].unique()[i]
        age_min = int(age_group.split('-')[0])
        age_max = int(age_group.split('-')[1])
        age_list += list(range(age_min,age_max+1))
        for cat in vals_dict.keys():
            vals_dict[cat] += [input_df.loc[input_df['Age Group']==age_group,cat].values[0] for _ in range(age_min,age_max+1)]
    return(vals_dict)
    
def create_child(plan,name,birth_year,input_df):
    # Create the child person object
    child = objs.plan.Person(name,birth_year,plan.cal_year,dependent=True)
    # Store the cost DataFrame in the child object
    child.child_cost_df = input_df.copy().reset_index(drop=True)
    plan.people.append(child)
    plan = create_child_expenses(plan,name,input_df)
    return(plan)

def create_child_expenses(plan,child_name,input_df):
    # Get Child
    child = plan.get_object_from_name("Person",child_name)
    # Get Values (Single Year Ages)
    vals_dict = expand_child_costs(input_df)
    
    for cat in vals_dict.keys():
        # Check if object exists already. If yes, append values to child_components attribute
        if cat == 'Childcare and Education':
            age_start = 6
            name = 'Education'
            if plan.get_id_from_name('Expense','Childcare','Joint') == None:
                childcare = objs.financial_objects.ExpenseObj(
                    'Joint',
                    "Necessary",
                    "Child",
                    'Childcare',
                    'Child or Dependent Care',
                    plan.cal_year,
                    pd.Series(vals_dict[cat][0:age_start], index=child.age.index[child.age.isin(range(0, age_start))]),
                    False,
                    False,
                    {
                        'infl_rate': plan.infl_rate,
                        'child_components': {child.id: pd.Series(vals_dict[cat][0:age_start], index=child.age.index[child.age.isin(range(0, age_start))])}
                    }
                ).standardize_timeseries(plan.cal_year)
                # Mark as future event object (child expenses are always future events)
                childcare.future_event = True
                plan.expenses.append(childcare)
                plan = childcare.project(plan)
            else:
                expense = plan.get_object_from_name('Expense','Education','Joint')
                expense.child_components |= {child.id:pd.Series(vals_dict[cat][age_start:18],index=child.age.index[child.age.isin(range(age_start,18))])}
                plan = expense.project(plan) 
                
                childcare = plan.get_object_from_name('Expense','Childcare','Joint')
                childcare.child_components |= {child.id:pd.Series(vals_dict[cat][0:age_start],index=child.age.index[child.age.isin(range(0,age_start))])}
                plan = childcare.project(plan)
        else:
            name = cat
            age_start = 0
        if plan.get_id_from_name('Expense',name,'Joint') == None:
            exp = objs.financial_objects.ExpenseObj(
                'Joint',
                "Necessary",
                "Child",
                name,
                "",
                plan.cal_year,
                pd.Series(vals_dict[cat][age_start:18], index=child.age.index[child.age.isin(range(age_start, 18))]),
                False,
                False,
                {
                    'infl_rate': plan.infl_rate,
                    'child_components': {child.id: pd.Series(vals_dict[cat][age_start:18], index=child.age.index[child.age.isin(range(age_start, 18))])}
                }
            ).standardize_timeseries(plan.cal_year)
            # Mark as future event object (child expenses are always future events)
            exp.future_event = True
            plan.expenses.append(exp)
            plan = exp.project(plan)
        else:
            expense = plan.get_object_from_name('Expense',name,'Joint')
            expense.child_components |= {child.id:pd.Series(vals_dict[cat][age_start:18],index=child.age.index[child.age.isin(range(age_start,18))])}
            plan = expense.project(plan) 
              
    return(plan)

def edit_child_expenses(plan,child_name,input_df):
    
    # Get Child
    child = plan.get_object_from_name("Person",child_name)
    # Get Values (Single Year Ages)
    vals_dict = expand_child_costs(input_df)
    print(vals_dict)
    
    for cat in vals_dict.keys():
        # Check if object exists already. If yes, append values to child_components attribute
        if cat == 'Childcare and Education':
            age_start = 6
            name = 'Education'
            if plan.get_id_from_name('Expense','Childcare','Joint') == None:
                print('Missing Expense: Childcare')
                return(plan)
            elif plan.get_id_from_name('Expense','Education','Joint') == None:
                print('Missing Expense: Education')
                return(plan)
            else:
                expense = plan.get_object_from_name('Expense','Education','Joint')
                expense.child_components[child.id] = pd.Series(vals_dict[cat][age_start:18],index=child.age.index[child.age.isin(range(age_start,18))])
                plan = expense.project(plan) 
 
                childcare = plan.get_object_from_name('Expense','Childcare','Joint')
                childcare.child_components[child.id] = pd.Series(vals_dict[cat][0:age_start],index=child.age.index[child.age.isin(range(0,age_start))])
                plan = childcare.project(plan)
        else:
            name = cat
            age_start = 0
            
        if plan.get_id_from_name('Expense',name,'Joint') == None:
            print('Missing Expense: ',name)
            return(plan)
        else:
            expense = plan.get_object_from_name('Expense',name,'Joint')
            expense.child_components[child.id] = pd.Series(vals_dict[cat][age_start:18],index=child.age.index[child.age.isin(range(age_start,18))])
            plan = expense.project(plan) 
              
    return(plan)