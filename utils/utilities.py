#####################
# UTILITY FUNCTIONS #
#####################

import numpy as np
import pandas as pd
import json as json
#from objs.plan import Plan, Individual
#from objs.financial_objects import objs.financial_objects.ExpenseObj, objs.financial_objects.objs.financial_objects.AssetObj, objs.financial_objects.LiabObj, objs.financial_objects.IncomeObj

import objs.plan
import objs.financial_objects

# General Utils:
# force_list has become expand_contract, which is an all-purpose
# equalizer for time series, meant to be indexed with the plan's cal_year 
# can optionally extend with zeros, for temporary objects

def json_to_object(json_string):
    """Convert JSON string to object."""
    load = json.loads(json_string)
    return(dict_to_object(load))    

def dict_to_object(dictionary):
    """Convert dictionary to appropriate object type."""
    if dictionary['obj_type'] == "Person":
        obj = objs.plan.Person('',0,pd.Series([0]),False,False)
    elif dictionary['obj_type'] == "Expense":
        obj = objs.financial_objects.ExpenseObj('', '', '', '','', pd.Series([0]), 0, False, False,{})
    elif dictionary['obj_type']=="Asset":
        obj = objs.financial_objects.AssetObj('', '', '', '','', pd.Series([0]), 0, 0, 0, False, False,{})
    elif dictionary['obj_type'] == "Liability":
        obj = objs.financial_objects.LiabObj('', '', '', '','', pd.Series([0]),0, 0, True, False,{'payment':0})
    elif dictionary['obj_type'] == 'Income':
        obj = objs.financial_objects.IncomeObj('', '', '', '', pd.Series([0]), 0, False, False,False,{})
    for key, value in dictionary.items():
        if key == 'counter':
            continue
        elif key == 'components':
            value = {key2:pd.Series(val2) for key2, val2 in value.items()}
            for key2 in value.keys():
                value[key2].index = value[key2].index.astype(int)
        elif key == 'child_cost_df' and value is not None:
            # Handle DataFrame deserialization for Person objects
            value = pd.DataFrame(value)
            value.index = pd.to_numeric(value.index)
        else:
            if isinstance(value,dict):
                if key == 'paired_attr': #set(value.keys()) == set(['series','time','share']):
                    value = {key:{key2:[[x[0],x[1],pd.Series(x[2]).set_axis(pd.Series(x[2]).index.astype(int))] if isinstance(x[2],dict) else [x[0],x[1],x[2]] for x in val2] for key2, val2 in value[key].items()} for key in ['series','time','share']}
                elif key == 'pension_params':
                    continue    
                else:
                    if isinstance(list(value.values())[0],list):
                        pass
                    elif isinstance(list(value.values())[0],dict):
                        value = pd.DataFrame(value)
                        value.index = pd.to_numeric(value.index)
                    else:
                        value = pd.Series(value)
                        value.index = pd.to_numeric(value.index)
        setattr(obj, key, value)
    return(obj)
    
def json_to_plan(json_string):
    """Convert JSON string to Plan object."""
    if isinstance(json_string,str):
        load_plan = json.loads(json_string)
    elif isinstance(json_string,dict):
        load_plan = json_string
    else:
        raise ValueError("Plan JSON must be a string or dict.")

    if not isinstance(load_plan, dict) or len(load_plan) == 0:
        raise ValueError("Plan JSON is empty or invalid.")

    # Basic validation for required fields
    required_keys = ['name','start_year','n_years','infl_rate','col_rate','cal_year',
                     'people','income','expenses','assets','liabilities','events','pairs','drawdown_order']
    missing_keys = [key for key in required_keys if key not in load_plan]
    if len(missing_keys) > 0:
        raise ValueError(f"Plan JSON missing keys: {', '.join(missing_keys)}")

    temp_plan = objs.plan.Plan("",0,0,0,0)
    for key, value in load_plan.items():
        if key in ['people','income','expenses','assets','liabilities']:
            if key == 'people':
                objs.plan.Person.counter = 0
            elif key == 'income':
                objs.financial_objects.IncomeObj.counter = 0
            elif key == 'expenses':
                objs.financial_objects.ExpenseObj.counter = 0  
            elif key == 'assets':
                objs.financial_objects.AssetObj.counter = 0
            else:
                objs.financial_objects.LiabObj.counter = 0 
            value = [dict_to_object(x) for x in load_plan[key]]
        elif key in ['tax_df','analytical_timeseries']:
            value = pd.DataFrame(value)
            value.index = pd.to_numeric(value.index)
        elif key == 'tax_df_dict':
            value = {key2:{key3:pd.DataFrame(value3,index=pd.to_numeric(pd.DataFrame(value3).index)) for key3, value3 in value2.items()} for key2, value2 in value.items()}
        else:
            if isinstance(value,dict) and key not in ['pairs','drawdown_order']:
                value = pd.Series(value)
                value.index = pd.to_numeric(value.index)
        setattr(temp_plan, key, value)
    return(temp_plan)

def expand_contract(series,cal_year,val_pad_front=True,val_pad_back=False,pad_vals=[0,0]):
    """
    Standardize time series to match plan calendar years.
    
    Args:
        series: Input series (can be scalar, list, or pandas Series)
        cal_year: Target calendar years
        val_pad_front: Whether to pad front with specified value
        val_pad_back: Whether to pad back with specified value
        pad_vals: Values to use for padding [front, back]
        
    Returns:
        Standardized pandas Series
    """
    if (isinstance(series,int) or isinstance(series,float)):
        series = pd.Series([series for _ in range(len(cal_year))],index=cal_year)
    elif isinstance(series,pd.Series):
        if len(series) > 0:
            min_year = min(series.index)
            max_year = max(series.index)
            #
            # Handle series with gaps in the middle
            new_index = range(min_year,max_year+1)
            series = pd.Series([series[i] if i in series.index else 0 for i in new_index],index=new_index)
            #
            min_val = series[series.index[0]]
            max_val = series[series.index[len(series)-1]]
            #
            if val_pad_front == True:
                pad_val_min = pad_vals[0]
            else:
                pad_val_min = min_val
            if val_pad_back == True:
                pad_val_max = pad_vals[1]
            else:
                pad_val_max = max_val
            
            min_cal_year = min(cal_year)
            max_cal_year = max(cal_year)
            if min_year <= min_cal_year:
                #prune
                series = series[range(min_cal_year,max_year+1)]
            else:
                #pad
                padding = pd.Series([pad_val_min for yr in range(min_cal_year,min_year)],index=list(range(min_cal_year,min_year)))
                series = pd.concat([padding,series])
            if max_year < max_cal_year:
                #pad
                padding = pd.Series([pad_val_max for yr in range(max_year+1,max_cal_year+1)],index=list(range(max_year+1,max_cal_year+1)))
                series = pd.concat([series,padding])
            else:
                #prune
                series = series[range(min_cal_year,max_cal_year+1)]
        else:
            series = pd.Series(0,index=cal_year)
    return(series)

# I think we still need an "inflate amount" for tax purposes

def inflate_amount(value,inflation_rate):
    """Apply cumulative inflation to a value over time."""
    # Should take in an objs.plan.Plan.infl_rate series, indexed with objs.plan.Plan.cal_year
    cumulative_infl = pd.Series([pd.Series(1+inflation_rate.loc[inflation_rate.index[0]:yr]).product() for yr in inflation_rate.index],index=inflation_rate.index)
    if isinstance(value,(float,int)):
        if value == np.inf:
            value_out = value*cumulative_infl
        else:
            value_out = (value*cumulative_infl).astype(int)
    elif isinstance(value,list):
        value_out = pd.Series([[int(val*infl) if val != np.inf else np.inf for val in value] for infl in cumulative_infl],index=cumulative_infl.index)
    return(value_out)

def inflate(self):
    self.value = expand_contract(self.value,self.cal_year)
    if self.fixed == True:
        pass
    else:
        self.infl_rate = expand_contract(self.infl_rate,self.cal_year)
        cumulative_infl = [pd.Series(1+self.infl_rate[self.cal_year[0]:yr]).product() for yr in self.cal_year]
        self.value = self.value * pd.Series(cumulative_infl)
    return(self)

# Object List Utilities
# zero_pad, prune, modify, merge

# Income:
# salary_from_GS
# salary_from_raises (unfinished)

# Assets:
# transfer

def transfer(from_asset,to_asset,amt,year):
    """Transfer money between assets."""
    from_asset.withdraw(amt,year)
    to_asset.deposit(amt,year)    

# Liabilities:
# pmt, ppmt, ipmt, term_months to payment

def pmt(PV,rate,term):
    """Calculate payment amount for loan amortization."""
    return((rate/12)*PV/(1-(1+rate/12)**(-term)))

def ppmt(PV,rate,P):
    """Calculate principal payment amount."""
    return(P-(rate/12)*PV)

def ipmt(PV,rate):
    """Calculate interest payment amount."""
    return((rate/12)*PV)

#Recover term from payment (instead of calculating payment from term)

def term_months_from_payment(present_value,rate,payment):
    """Calculate loan term in months from payment amount."""
    return(int(-np.log(1-present_value/(payment/(rate/12)))/np.log(1+rate/12))+1)

def compute_pension_accrued_income(salary: pd.Series,
                                   cal_year: pd.Series,
                                #    accrual_rate: float = 0.015,
                                   service_start_year: int | None = None,
                                   vesting_years: int = 5,
                                   final_avg_years: int = 3,
                                   retirement_age: int = 65,
                                   person_age_series: pd.Series | None = None) -> pd.Series:
    """Compute accrued pension income for each year based on salary and service."""
    base_year = int(cal_year.iloc[0]) if service_start_year is None else service_start_year
    years_of_service = pd.Series([max(0, int(y) - base_year + 1) for y in cal_year], index=cal_year)
    vested = (years_of_service >= vesting_years).astype(int)
    salary = expand_contract(salary, cal_year)
    final_avg = salary.rolling(final_avg_years, min_periods=1).mean()
    # Compute using California 2 @ 62:
    pension = 0.01 * (1 + 0.1*(retirement_age - 52)) * years_of_service * final_avg * vested
    # Federal
    # pension = 0.01 * years_of_service.apply(lambda x: 1.1 if x >= 20 else 1) * years_of_service * final_avg * vested
    
    # We'll handle the actual retirement and income at a later time
    # once the retirement event is developed.

    # if person_age_series is not None:
    #     ages = expand_contract(person_age_series, cal_year)
    #     if (ages >= retirement_age).any():
    #         first_ret_year = int(ages.index[(ages >= retirement_age)][0])
    #         pension.loc[first_ret_year:] = pension.loc[first_ret_year]
    return(pension)

def get_all_descendants(plan, obj_id):
    """
    Find all descendant objects recursively across all networks.
    
    Args:
        plan: The plan object containing object networks
        obj_id: ID of the object to find descendants for
        
    Returns:
        Dictionary with separate lists for each network (series, time, share)
    """
    descendants = {'series': set(), 'time': set(), 'share': set()}
    
    # Use a queue to process all descendants iteratively
    to_process = [obj_id]
    processed = set()
    
    while to_process:
        current_id = to_process.pop(0)
        if current_id in processed:
            continue
        processed.add(current_id)
        
        # Find all children of current_id in each network
        for network in ['series', 'time', 'share']:
            for pair in plan.pairs[network]:
                if pair[0] == current_id:  # current_id is parent, pair[1] is child
                    child_id = pair[1]
                    descendants[network].add(child_id)
                    to_process.append(child_id)
    
    # Convert sets to lists for consistency
    return {network: list(descendants[network]) for network in descendants}

def get_all_ancestors(plan, obj_id):
    """
    Find all ancestor objects recursively across all networks.
    
    Args:
        plan: The plan object containing object networks
        obj_id: ID of the object to find ancestors for
        
    Returns:
        Dictionary with separate lists for each network (series, time, share)
    """
    ancestors = {'series': set(), 'time': set(), 'share': set()}
    
    # Use a queue to process all ancestors iteratively
    to_process = [obj_id]
    processed = set()
    
    while to_process:
        current_id = to_process.pop(0)
        if current_id in processed:
            continue
        processed.add(current_id)
        
        # Find all parents of current_id in each network
        for network in ['series', 'time', 'share']:
            for pair in plan.pairs[network]:
                if pair[1] == current_id:  # current_id is child, pair[0] is parent
                    parent_id = pair[0]
                    ancestors[network].add(parent_id)
                    to_process.append(parent_id)
    
    # Convert sets to lists for consistency
    return {network: list(ancestors[network]) for network in ancestors}

def get_all_related_objects(plan, obj_id):
    """
    Get all objects related to a given object ID (both ancestors and descendants).
    
    Args:
        plan: The plan object containing the object networks
        obj_id: The ID of the object to find related objects for
        
    Returns:
        set: Set of all related object IDs (ancestors + descendants + self)
    """
    ancestors = get_all_ancestors(plan, obj_id)
    descendants = get_all_descendants(plan, obj_id)
    
    # Combine all related IDs
    related_ids = {obj_id}  # Include self
    for network in ['series', 'time', 'share']:
        related_ids.update(ancestors[network])
        related_ids.update(descendants[network])
    
    return related_ids

def get_future_event_object_ids(plan):
    """Get all object IDs related to future events (including descendants)."""
    future_event_ids = set()
    
    # Get all objects marked as future events
    for obj_list in [plan.assets, plan.expenses, plan.liabilities, plan.income]:
        for obj in obj_list:
            if obj.future_event:
                future_event_ids.add(obj.id)
    
    return future_event_ids