#####################
# FINANCIAL OBJECTS #
#####################


import pandas as pd
import numpy as np
import json as json
import copy

# import sys
# sys.path.append('../utils')

#from utilities import expand_contract,term_months_from_payment,pmt,ppmt,ipmt
import utils.utilities


# Class hierarchy
 
# FinObj:
# |
# + IncExpObj
#   |
#   + IncomeObj
#     |
#   + ExpenseObj
#     |
# + AssetObj
#   |
# + LiabObj
#   |


class FinObj:
    """Base class for all financial objects (Income, Expenses, Assets, Liabilities)."""
    
    def __init__(self,obj_type,person,cat,subcat,name,cal_year,value,editable,attributes={}):
        
        #Set ID (str)
        self.plan_id = 1 #plan_id
        
        #Set Classifications (str)
        self.person = person
        self.obj_type = obj_type
        self.category = cat
        self.subcategory = subcat
        self.name = name
        self.editable = editable
        
        # Track if this object was created by a future event
        self.future_event = False
        
        # Set Time
        self.cal_year = cal_year

        if 'start_year' in attributes.keys():
            self.start_year = attributes['start_year']
        else:
            self.start_year = int(cal_year[0])
        if 'end_year' in attributes.keys():
            self.end_year = attributes['end_year']
        else:
            self.end_year = int(self.cal_year[len(self.cal_year)-1])   
        
        # Set Value            
        if not isinstance(value,pd.Series):
            self.value = pd.Series(value,index=self.cal_year)
        else:
            self.value = value
        
        # Set Object Network 
        self.dependent_objs = False #can be changed with attributes
        self.paired_attr = {'series':{},'time':{},'share':{}}
        
        # Set other attributes
        for key, value in attributes.items():
            setattr(self, key, value)
        
    def to_dataframe(self):
        """Convert object to pandas DataFrame."""
        return(pd.DataFrame({x:self.__dict__[x] for x in self.__dict__ if x[0] != '_' and x != 'cal_year'},index=self.cal_year))
    
    def to_serializable(self):
        """Convert object to JSON-serializable format."""
        out = copy.deepcopy({key:(value.to_dict() if isinstance(value,(pd.Series,pd.DataFrame)) else value) for key, value in self.__dict__.items()})
        return(out)
        
    def standardize_timeseries(self,cal_year):
        """Standardize time series to match plan calendar years."""
        self.cal_year = cal_year
        all_series = [x for x in self.__dict__.keys() if x[0] != '_' and isinstance(self.__dict__[x],pd.Series) and x != 'cal_year']
        all_dicts = [x for x in self.__dict__.keys() if x[0] != '_' and isinstance(self.__dict__[x],dict)]
        for series in all_series:
            self.__dict__[series] = utils.utilities.expand_contract(self.__dict__[series],cal_year,val_pad_front=True,val_pad_back=True)
        for dict_ in all_dicts:
            for key in self.__dict__[dict_].keys():
                if isinstance(self.__dict__[dict_][key],pd.Series):
                    self.__dict__[dict_][key] = utils.utilities.expand_contract(self.__dict__[dict_][key],cal_year,val_pad_front=True,val_pad_back=True)
        return(self)

    def project(self,plan,init_id=None):
        """
        Main projection method that updates object values and resolves dependencies.
        
        Args:
            plan: The plan object containing all financial objects
            init_id: ID of initial object to prevent infinite loops
            
        Returns:
            Updated plan object
        """
        # First, make sure the timeseries are the right length
        self = self.standardize_timeseries(plan.cal_year)
        
        # First, we have to check if the object is a child expense object and recompute
        # its value based on the child_components, in case they have changed
        if "child_components" in self.__dict__.keys():
            self.value_input = sum([x for x in self.child_components.values()])

        # Next, for each of the three networks, pull any paired attributes
        # SERIES
        temp_series = {}
        for parent in self.paired_attr['series'].keys():
            # Employer match should only have one parent - the income paired with the 401k
            if self.subcategory == 'Employer Match':
                props_list = []
                cap_series_list = []
                for pair in self.paired_attr['series'][parent]:
                    pair_prop = pair[2]
                    if isinstance(pair_prop,(list,tuple)) and len(pair_prop) == 2:
                        prop, cap = pair_prop
                    else:
                        prop, cap = pair_prop, None
                    props_list.append(utils.utilities.expand_contract(prop, self.cal_year))
                    if cap is not None:
                        infl_rate = utils.utilities.expand_contract(plan.infl_rate, self.cal_year)
                        cap_start_year = int(self.start_year)
                        cumulative_infl = [
                            1 if yr == cap_start_year else pd.Series(1+infl_rate.loc[cap_start_year:yr-1]).product()
                            for yr in self.cal_year
                        ]
                        if isinstance(cap, pd.Series):
                            cap_series = utils.utilities.expand_contract(cap, self.cal_year)
                        else:
                            cap_series = pd.Series(cap, index=self.cal_year)
                        cap_series = cap_series * pd.Series(cumulative_infl,index=self.cal_year)
                        cap_series_list.append(cap_series)
                props = pd.concat(props_list, axis=1).min(axis=1)
                series_val = props * getattr(plan.get_object_from_id(parent),self.paired_attr['series'][parent][0][0])
                if len(cap_series_list) > 0:
                    cap_series = pd.concat(cap_series_list, axis=1).min(axis=1)
                    series_val = series_val.combine(cap_series, min)
                setattr(self,
                        self.paired_attr['series'][parent][0][1],
                        series_val)
            else:
                for pair in self.paired_attr['series'][parent]:
                    pair_prop = pair[2]
                    if isinstance(pair_prop,(list,tuple)) and len(pair_prop) == 2:
                        prop, cap = pair_prop
                    else:
                        prop, cap = pair_prop, None
                    props = utils.utilities.expand_contract(prop, self.cal_year)
                    series_val = props * getattr(plan.get_object_from_id(parent),pair[0])
                    if cap is not None:
                        infl_rate = utils.utilities.expand_contract(plan.infl_rate, self.cal_year)
                        cap_start_year = int(self.start_year)
                        cumulative_infl = [
                            1 if yr == cap_start_year else pd.Series(1+infl_rate.loc[cap_start_year:yr-1]).product()
                            for yr in self.cal_year
                        ]
                        if isinstance(cap, pd.Series):
                            cap_series = utils.utilities.expand_contract(cap, self.cal_year)
                        else:
                            cap_series = pd.Series(cap, index=self.cal_year)
                        cap_series = cap_series * pd.Series(cumulative_infl,index=self.cal_year)
                        series_val = series_val.combine(cap_series, min)

                    if pair[1] not in temp_series:
                        temp_series |= {pair[1]:series_val}
                    else:
                        temp_series[pair[1]] += series_val
        for key in temp_series.keys():
            # Prevent negative expense values for asset-driven contributions
            if self.obj_type == 'Expense' and key == 'value':
                for parent_id, pairs in self.paired_attr['series'].items():
                    for pair in pairs:
                        if pair[1] == 'value' and pair[0] == 'contribution':
                            parent_obj = plan.get_object_from_id(parent_id)
                            if parent_obj is not None and parent_obj.obj_type == 'Asset':
                                temp_series[key] = temp_series[key].apply(lambda x: max(x,0))
                                break
            setattr(self,key,temp_series[key])
                    
        # TIME
        for parent in self.paired_attr['time'].keys():
            # Should only be one parent for time at the moment...
            # We'll store end_year just in case we need it for a sale
            end_year = self.end_year
            
            for pair in self.paired_attr['time'][parent]:
                setattr(self,
                        pair[1],
                        getattr(plan.get_object_from_id(parent),pair[0])+pair[2])
                # If there is an asset that is receiving end_year and has been sold before, reverse sale and resell
                if self.obj_type == 'Asset' and pair[1] == 'end_year':
                    if self.sold == 1:
                        plan = self.reverse_sale(plan,end_year) # Sale is reversed, we'll make the new sale after updating
        
        # SHARE PROPS
        # Any newly created Joint Expenses will get caught here and finish their
        # initialization through the first update() call
        if self.obj_type == 'Expense' and self.person == 'Joint':
            if 'share_props' not in self.__dict__.keys():
                self = self.set_props(plan)


                # Update (inflate for income/expenses, update for assets, amort_annual for liabilities)
        self = self.update().standardize_timeseries(plan.cal_year)
        
        # If this object is an asset that needs to be resold, after being reversed above
        if self.obj_type == 'Asset':
            if self.sold == -1:
                plan = self.sell(plan,self.end_year)

        # Any joint assets, liabiliites, or income will be split equally into components
        # After the update
        if self.obj_type != 'Expense':
            if self.person == 'Joint':
                self.components = {person.id:(self.value*0.5).astype(int) for person in plan.people if person.dependent==False}
            else:
                self.components = {self.person:self.value.astype(int)}
        
        # Update all dependent objects, passing the object_id of the first object to
        # be projected. If the projection encounters a loop in the dependence network,
        # It will break out after projecting the initial object a second time.
        if init_id == self.id:
            return(plan)
        else:
            if init_id == None:
                init_id = self.id
                
             # Project all child objects dependent on current object, and pass init_id 
             # to prevent a loop
            if self.dependent_objs == True:
                for child_id in [pair[1] for lst in plan.pairs.values() for pair in lst if pair[0]==self.id]:
                    child_obj = plan.get_object_from_id(child_id)
                    if child_obj is None:
                        continue
                    plan = child_obj.project(plan,init_id)
        
        return(plan)
    
    
###############################################################################

class IncExpObj(FinObj):
    """Base class for Income and Expense objects."""
    
    def __init__(self,obj_type,person,cat,subcat,name,cal_year,value,fixed,editable,attributes):
        super().__init__(obj_type,person,cat,subcat,name,cal_year,value,editable,attributes)
        self.fixed = fixed
        
        #Income and Expense objects will always retain a copy of their uniflated value
        if self.fixed == False:
            self.value_input = self.value
        # for key in attributes.keys():
        #     setattr(self,key,attributes[key])

    def inflate(self):
        """Apply inflation to income/expense values over time."""
        if self.fixed == True:
            pass
        else:
            self.value_input = utils.utilities.expand_contract(self.value_input,self.cal_year)#.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):])
            self.infl_rate = utils.utilities.expand_contract(self.infl_rate,self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):])
            base_year = int(self.start_year)
            cumulative_infl = [
                1 if yr == base_year else pd.Series(1+self.infl_rate.loc[base_year:yr-1]).product()
                for yr in self.cal_year
            ]
            self.value = (self.value_input * pd.Series(cumulative_infl,index=self.cal_year)).astype(int)
        self.value = utils.utilities.expand_contract(self.value.loc[self.start_year:self.end_year],self.cal_year,val_pad_front=True,val_pad_back=True).astype(int)
        return(self)
    
    def deflate(self):
        """Remove inflation from values (DEPRECATED - used in frontend)."""
       # self.value = utils.utilities.expand_contract(self.value,self.cal_year)
        if self.fixed == True:
            pass
        else:
            self.infl_rate = utils.utilities.expand_contract(self.infl_rate,self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):])
            base_year = int(self.start_year)
            cumulative_infl = [
                1 if yr == base_year else pd.Series(1+self.infl_rate.loc[base_year:yr-1]).product()
                for yr in self.cal_year
            ]
            self.value = (self.value / pd.Series(cumulative_infl,index=self.cal_year)).astype(int)
        return(self)
    

###############################################################################

class IncomeObj(IncExpObj):
    """Represents income sources (salary, pension, etc.)."""
    counter = 0

    def __init__(self,person,cat,subcat,name,cal_year,value,fixed,taxable,editable,attributes={}):
        super().__init__('Income',person,cat,subcat,name,cal_year,value,fixed,editable,attributes)
        IncomeObj.counter += 1
        self.id = 'Income_' + str(IncomeObj.counter)
        
        # Only income-specific attribute is taxable
        self.taxable = taxable

        # Optional payroll tax add-ons (list of dicts: {'name': str, 'rate': float})
        if not hasattr(self, 'payroll_taxes') or self.payroll_taxes is None:
            self.payroll_taxes = []
        
        # If joint income is added in the future, components will be added here too
    
    def update(self):
        """Update income values and calculate pension if configured."""
        # Compute pension if configured
        if hasattr(self, 'pension_params'):
            person_age = getattr(self, 'age', None)  # IncomeObj doesn't have age, but could inherit from Person
            
            self.pension = utils.utilities.compute_pension_accrued_income(
                salary=self.value,
                cal_year=self.cal_year,
                **self.pension_params,
                person_age_series=person_age
            ).astype(int)
        
        self.inflate()
        return(self)
    
    def make_pension_asset(self, plan,
                           contribution_rate=0.06,
                           service_start_year=None,
                           vesting_years=5,
                           final_avg_years=3,
                           retirement_age=65,
                           asset_multiplier=25):
        """
        Create pension-related objects (contribution expense and synthetic asset).
        
        Args:
            plan: The plan object
            contribution_rate: Pension contribution rate as decimal
            service_start_year: Year service started (defaults to plan start)
            vesting_years: Years to vest
            final_avg_years: Years for final average calculation
            retirement_age: Age at retirement
            asset_multiplier: Multiplier to convert pension to asset value
            
        Returns:
            Updated plan object
        """
        # configure pension on this income
        self.pension_params = {
            'service_start_year': int(plan.cal_year.iloc[0]) if service_start_year is None else service_start_year,
            'vesting_years': vesting_years,
            'final_avg_years': final_avg_years,
            'retirement_age': retirement_age,
        }
        self.dependent_objs = True

        # Create pension contribution expense (paired to income value)
        contribution_exp = ExpenseObj(
            person=self.person,
            cat='Savings',
            subcat='Retirement',
            name=f'Pension Contribution ({plan.get_object_from_id(self.person).name})',
            tax_keyword='Traditional',
            cal_year=plan.cal_year,
            value=0,
            fixed=True,
            editable=False,
            attributes={'start_year': int(plan.cal_year.iloc[0]), 'end_year': int(plan.cal_year.iloc[-1])}
        )
        # The contribution expense is paired to the income value with the contribution rate
        contribution_exp.paired_attr['series'] |= {self.id: [['value', 'value', contribution_rate]]}
        contribution_exp.paired_attr['time'] |= {self.id: [['start_year', 'start_year', 0], ['end_year', 'end_year', 0]]}
        plan.pairs['series'].append([self.id, contribution_exp.id])
        plan.pairs['time'].append([self.id, contribution_exp.id])
        plan.expenses.append(contribution_exp)

        # Synthetic retirement asset driven by parent's pension series
        asset = AssetObj(
            person=self.person,
            cat='Investment',
            subcat='Retirement',
            name='Pension Equivalent',
            tax_keyword='',
            cal_year=plan.cal_year,
            value=0,
            growth_rate=0.0,
            contribution=0,
            interest=False,
            editable=False,
            attributes={'start_year': int(plan.cal_year.iloc[0]), 'end_year': int(plan.cal_year.iloc[-1]), 'ui_hidden': True}
        )
        asset.paired_attr['series'] |= {self.id: [['pension', 'value', asset_multiplier]]}
        asset.paired_attr['time'] |= {self.id: [['start_year', 'start_year', 0], ['end_year', 'end_year', 0]]}
        plan.pairs['series'].append([self.id, asset.id])
        plan.pairs['time'].append([self.id, asset.id])
        plan.assets.append(asset)

        # Project to compute pension and push to asset and expense
        plan = self.project(plan)
        return plan
    
    def remove_pension(self, plan):
        """Remove pension configuration and all related objects from the plan."""
        if not hasattr(self, 'pension_params'):
            return plan  # No pension to remove
        
        # Find all child objects that depend on this income for pension
        child_ids = []
        for pair_list in plan.pairs.values():
            for pair in pair_list:
                if pair[0] == self.id:
                    child_obj = plan.get_object_from_id(pair[1])
                    if child_obj is not None:
                        # Check if this child is pension-related
                        if (child_obj.obj_type == 'Expense' and 
                            child_obj.name.startswith('Pension Contribution')):
                            child_ids.append(pair[1])
                        elif (child_obj.obj_type == 'Asset' and 
                              child_obj.name == 'Pension Equivalent'):
                            child_ids.append(pair[1])
        child_ids = list(set(child_ids))
        
        # Remove all pension-related child objects
        for child_id in child_ids:
            try:
                plan = plan.remove_object_by_id(child_id)
            except Exception as e:
                print(f"Error removing pension child object {child_id}: {e}")
        
        # Clean up pension attributes from this income object
        if hasattr(self, 'pension'):
            delattr(self, 'pension')
        if hasattr(self, 'pension_params'):
            delattr(self, 'pension_params')
        
        # Mark as no longer dependent
        self.dependent_objs = False
        
        return plan
    
    def get_pension_contribution_rate(self, plan):
        """Get current pension contribution rate from related expense object."""
        if not hasattr(self, 'pension_params'):
            return None
        
        # Find the pension contribution expense
        for pair_list in plan.pairs.values():
            for pair in pair_list:
                if pair[0] == self.id:
                    child_obj = plan.get_object_from_id(pair[1])
                    if (child_obj is not None and 
                        child_obj.obj_type == 'Expense' and 
                        child_obj.name.startswith('Pension Contribution')):
                        # Get the contribution rate from the paired attributes
                        if self.id in child_obj.paired_attr['series']:
                            for attr_pair in child_obj.paired_attr['series'][self.id]:
                                if attr_pair[0] == 'value' and attr_pair[1] == 'value':
                                    return attr_pair[2]
        return None

    def add_payroll_tax(self, tax_name, tax_rate):
        """Add a payroll tax add-on for this income."""
        if not hasattr(self, 'payroll_taxes') or self.payroll_taxes is None:
            self.payroll_taxes = []
        self.payroll_taxes.append({'name': tax_name, 'rate': float(tax_rate)})
        return self

    def remove_payroll_tax(self, tax_index):
        """Remove a payroll tax add-on by list index."""
        if not hasattr(self, 'payroll_taxes') or self.payroll_taxes is None:
            self.payroll_taxes = []
        if 0 <= tax_index < len(self.payroll_taxes):
            self.payroll_taxes.pop(tax_index)
        return self
        
###############################################################################        

class ExpenseObj(IncExpObj):
    """Represents expenses (necessary, discretionary, savings)."""
    counter = 0
    
    def __init__(self,person,cat,subcat,name,tax_keyword,cal_year,value,fixed,editable,attributes={}):
        super().__init__('Expense',person,cat,subcat,name,cal_year,value,fixed,editable,attributes)
        ExpenseObj.counter += 1
        self.id = 'Expense_' + str(ExpenseObj.counter)
        
        # Expenses have a tax keyword for use in balance_and_tax
        self.tax_keyword = tax_keyword
        
        # Components - each person's share of the expense value
        # Joint is set below
        if self.person != 'Joint':
            self.components = {self.person:self.value}
            
        #self.share_props is uninitiated, as it will only be set for joint objects
        
    def set_props(self,plan):
        """Set proportional sharing properties for joint expenses."""
        if(self.person != 'Joint'):
            return(self)
        else:
            plan = plan.generate_expense_share()
            self.share_props = plan.share_props
            adults = [person.id for person in plan.people if person.dependent == False]
            all_income = [obj.id for obj in plan.income if (obj.person in adults) and (obj.category == 'Earned')]
            #
            self.paired_attr['share'] |= {inc:[['value','share_props',None]] for inc in all_income}
            self.components = {person_id:None for person_id in adults}
            self = self.adjust_share()
            return(self)
        
    def adjust_share(self):
        """Adjust expense sharing proportions based on income ratios."""
        if('share_props' not in self.__dict__.keys()):
            return(self)
        else:
            for person_id in self.components.keys():
                if person_id == 'Person_1':
                    self.components[person_id] = (self.value*self.share_props).astype(int)
                else:
                    self.components[person_id] = (self.value*(1-self.share_props)).astype(int)

            return(self)
        
    def update(self):
        if 'child_components' in self.__dict__.keys():
            n_kids = sum([pd.Series([1 if x > 0 else 0 for x in self.child_components[key]],index=self.cal_year) for key in self.child_components.keys()])
            multipliers = pd.Series([0 if x == 0 else (1.24 if x == 1 else (1 if x == 2 else 0.76)) for x in n_kids],index=self.cal_year)
            self.value = (sum(self.child_components.values())*multipliers).astype(int)
        self.inflate()
        if self.person == 'Joint':
            self = self.adjust_share()
        else:
            self.components[self.person] = self.value.astype(int)
        return(self)

    
###############################################################################

class AssetObj(FinObj):
    """Represents assets (retirement accounts, savings, real estate, etc.)."""
    counter = 0
    
    def __init__(self,person,cat,subcat,name,tax_keyword,cal_year,value,growth_rate,contribution,interest,editable,attributes={}):
        super().__init__('Asset',person,cat,subcat,name,cal_year,value,editable,attributes)
        AssetObj.counter +=1
        self.id = 'Asset_' + str(AssetObj.counter)
        
        #
        self.growth_rate = growth_rate
        self.contribution = contribution
        self.transaction = pd.Series([0 for yr in self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):]],index=self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):])
        self.tax_keyword = tax_keyword
        self.interest = interest
        #self.liab_value = utils.utilities.expand_contract(0,self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):])
        if 'props' in self.__dict__.keys():
            self.props = utils.utilities.expand_contract(self.props,self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):])
        if 'secondary_contribution' not in self.__dict__.keys():
            self.secondary_contribution = pd.Series([0 for yr in self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):]],index=self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):])
    
        # Track if there is a sell action taken with this asset (at self.end_year)
        self.sold = 0; #0 = never sold, 1 is sold at some point, -1 has had sale reversed, and need to resell.
    
    def update(self):
        """Update asset values using compound growth formula."""
        for attr in ['growth_rate','value','contribution','secondary_contribution','transaction']:
            setattr(self,attr,utils.utilities.expand_contract(getattr(self,attr),self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):]))
        
        # Go into the loop if the value is not in the paired attributes
        if 'value' not in [item[1] for sublist in self.paired_attr['series'].values() for item in sublist]:
            temp_val = []
            for yr in self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):]:
                if yr == self.start_year:
                    temp_val.append(self.value[yr])
                else:
                    temp_val.append(temp_val[-1]*(1+self.growth_rate[yr])+self.contribution[yr]+self.secondary_contribution[yr]+self.transaction[yr])
            self.value = pd.Series(temp_val,index=self.cal_year.loc[(self.cal_year[self.cal_year==self.start_year].index[0]):]).astype(int)
        
        self = self.standardize_timeseries(self.cal_year)
        self.gains = self.value.diff(1).shift(-1)
        
        #self.equity = self.value - self.liab_value
        return(self)     
    
    def make_expense_obj(self,plan,keyword,props=1.0,cap=None):
        """Create related expense objects (contribution, maintenance, tax)."""
        if keyword == 'contribution':
            exp_obj = ExpenseObj(self.person,'Savings',self.subcategory,self.name,self.tax_keyword,self.cal_year,0,
                                 True,False,
                                 {'start_year':self.start_year,'end_year':self.end_year})
            exp_obj.paired_attr['series'] |= {self.id:[['contribution','value',1.0]]}
            exp_obj.paired_attr['time'] |= {self.id:[['start_year','start_year',0],['end_year','end_year',0]]}
        elif keyword == 'maintenance':
            exp_obj = ExpenseObj(self.person,'Necessary',self.name,self.name+' Maintenance','',self.cal_year,self.value,
                                 True,False,
                                 {'start_year':self.start_year,'end_year':self.end_year})
            prop_value = (props, cap) if (cap is not None and cap > 0) else props
            exp_obj.paired_attr['series'] |= {self.id:[['value','value',prop_value]]}
            exp_obj.paired_attr['time'] |= {self.id:[['start_year','start_year',0],['end_year','end_year',0]]}

        elif keyword == 'tax':
            exp_obj = ExpenseObj(self.person,'Tax','Property','Property Tax','Property Tax',self.cal_year,self.value,
                                 True,False,
                                 {'start_year':self.start_year,'end_year':self.end_year})
            exp_obj.paired_attr['series'] |= {self.id:[['value','value',props]]}
            exp_obj.paired_attr['time'] |= {self.id:[['start_year','start_year',0],['end_year','end_year',0]]}

        # Mark as future event object if the parent asset is a future event
        if self.future_event:
            exp_obj.future_event = True

        self.dependent_objs = True
        plan.expenses.append(exp_obj)
        plan = exp_obj.project(plan)
        plan.pairs['series'].append([self.id,exp_obj.id])
        plan.pairs['time'].append([self.id,exp_obj.id])
        return(plan)
    
    def make_401k_objs(self,plan,inc_obj_id,props,match_prop_max):
        """Create 401k and related objects (contribution expense, employer match)."""
        # Pair asset with income
        inc_obj = plan.get_object_from_id(inc_obj_id)
        inc_obj.dependent_objs = True
        
        # Make the Salary Proportion -> Contribution
        #self.contribution = (inc_obj.value*self.props).astype(int)
        self.paired_attr['series'] |= {inc_obj.id:[['value','contribution',props]]}
        self.paired_attr['time'] |= {inc_obj.id:[['start_year','start_year',0],['end_year','end_year',0]]}
        #
        plan.pairs['series'].append([inc_obj.id,self.id])
        plan.pairs['time'].append([inc_obj.id,self.id])
        
        # Make expense object for contribution
        plan = self.make_expense_obj(plan,'contribution')
        self.dependent_objs = True

        # Compute secondary contribution
        #self.match_props = pd.concat([self.props,self.match_props_max], axis=1).min(axis=1)
        #self.secondary_contribution = (self.match_props*inc_obj.value).astype(int)

        # Make match income object dependent on income, with two sets of props (min to be determined)
        match_obj = IncomeObj(self.person,'External','Employer Match',self.name,self.cal_year,0,
                             True,False,False,
                             {'start_year':self.start_year,'end_year':self.end_year})
        match_obj.paired_attr['series'] |= {inc_obj.id:[['value','value',props],['value','value',match_prop_max]]}
        match_obj.paired_attr['time'] |= {inc_obj.id:[['start_year','start_year',0],['end_year','end_year',0]]}
        #
        plan.pairs['series'].append([inc_obj.id,match_obj.id])
        plan.pairs['time'].append([inc_obj.id,match_obj.id])
        #
        match_obj.dependent_objs = True
        plan.income.append(match_obj)
        
        # Make a link between the employer match and the secondary contribution for the 401k
        self.paired_attr['series'] |= {match_obj.id:[['value','secondary_contribution',1.0]]}
        plan.pairs['series'].append([match_obj.id,self.id])
        
        # Project the income object, triggering the subnetwork
        plan = inc_obj.project(plan)
        
        return(plan)
    
    def sell(self,plan,year,prune=False):
        """Sell asset and handle proceeds distribution."""
        # What to do if there is no drawdown (i.e. sell without a savings account...weird)
        liab_ids = [pair[0] for pair in plan.pairs['series'] if pair[1]==self.id and pair[0].split('_')[0] == 'Liability']

        # If prune is true, then manually set the end_years of the asset (and liability)
        if prune == True:
            self.end_year = year
            #
            if len(liab_ids) > 0:
                liab_id = liab_ids[0]
                liab_obj = plan.get_object_from_id(liab_id)
                liab_obj.end_year = year #Manually adjust liability end_year
                #
                plan = plan.get_object_from_id(liab_id).project(plan)
            else:
                plan = self.project(plan)
            
        # If prune is false, then a time pairing is handling that aspect prior
        # to this method, and the asset can just be sold
        
        people = list(self.components.keys())
        for person in people:
            asset_value = self.components[person][year]
            if len(liab_ids) > 0:
                liab_value = plan.get_object_from_id(liab_ids[0]).components[person][year]
            else:
                liab_value = 0
            net = asset_value - liab_value
            if net >= 0:
                plan.get_object_from_id(plan.drawdown_order[person][0]).deposit(net,year)
            else:
                plan.drawdown(net,year,person,'transaction')
        
        # Change sell state
        self.sold = 1
        
        return(plan)
    
    def reverse_sale(self,plan,year,prune=False):
        """Reverse a previous asset sale."""
        # Undoes the operations of .sell() - sets end_year to max(cal_year) and 
        # Reverse the deposit (or put into drawdown[0])
        liab_ids = [pair[0] for pair in plan.pairs['series'] if pair[1]==self.id and pair[0].split('_')[0] == 'Liability']

        # If prune is true, then manually set the end_years of the asset (and liability)
        if prune == True:
            self.end_year = max(self.cal_year)
            #
            if len(liab_ids) > 0:
                liab_id = liab_ids[0]
                liab_obj = plan.get_object_from_id(liab_id)
                liab_obj.end_year = self.end_year #Manually adjust liability end_year
                #
                plan = plan.get_object_from_id(liab_id).project(plan)
            else:
                plan = self.project(plan)
            
        # If prune is false, then a time pairing is handling that aspect prior
        # to this method, and the asset can just be sold
        
        people = list(self.components.keys())
        for person in people:
            asset_value = self.components[person][year]
            if len(liab_ids) > 0:
                liab_value = plan.get_object_from_id(liab_ids[0]).components[person][year]
            else:
                liab_value = 0
            net = asset_value - liab_value
            if net >= 0:
                plan.get_object_from_id(plan.drawdown_order[person][0]).withdrawal(net,year)
            else:
                plan.get_object_from_id(plan.drawdown_order[person][0]).deposit(net,year)
        
        # Change sell state
        self.sold = -1

        return(plan)
                
    def deposit(self,amt,year):
        """Add money to asset."""
        self.transaction[year] += amt
        return(self)

    def withdrawal(self,amt,year):
        """Remove money from asset (for partial sales)."""
        self.deposit(-amt,year)
        return(self)
    
###############################################################################

class LiabObj(FinObj):
    """Represents liabilities (mortgages, loans, credit cards)."""
    counter = 0
    
    def __init__(self,person,cat,subcat,name,tax_keyword,cal_year,interest_rate,value,existing,editable,attributes):
        super().__init__('Liability',person,cat,subcat,name,cal_year,value,editable,attributes)
        LiabObj.counter += 1
        self.id = 'Liability_' + str(LiabObj.counter)
        self.interest_rate = interest_rate
        self.existing = existing
        self.tax_keyword = tax_keyword
        #
        if self.existing:
            if 'principal' in attributes.keys():
                self.principal = attributes['principal']
            self.present_value = value
            self.payment = attributes['payment']
            if self.payment > 0:
                self.term = utils.utilities.term_months_from_payment(self.present_value,self.interest_rate,self.payment)
                self.term_in_years = False
                self.extra_payment = [0 for yr in range(self.term)]
        else:
            self.principal = value
            if attributes['down_pct']:
                down_payment = attributes['down_payment']*self.principal
            else:
                down_payment = attributes['down_payment']
            self.term = attributes['term']
            self.term_in_years = attributes['term_in_years']
            if(self.term_in_years):
                self.term = 12*self.term
                self.term_in_years = False
            self.extra_payment = [0 for yr in range(self.term)]
            self.present_value = self.principal-down_payment #self.down_payment
            
        # Start with any empty asset, if one is paired, it will be updated in .project()    
        self.asset_value = pd.Series(0,index=self.cal_year)
        # Backward-compatible alias for legacy usage
        self.asset_val = self.asset_value
        
        if self.subcategory=='Mortgage':
            self.pmi_rate = attributes['pmi_rate']
            self.pmi_thresh_pct = attributes['pmi_thresh_pct']
            
        
    def amortize(self):
        """Calculate amortization schedule for liability."""
        self.payment = utils.utilities.pmt(self.present_value,self.interest_rate,self.term)
        year, mon, time_interp, period, ppay, ipay, pay = [[],[],[],[],[],[],[]]
        value = [self.present_value]
        epay = list(self.extra_payment)
        for i in range(self.term):
            pv = value[-1]
            p = min(self.payment,pv*(1+(self.interest_rate/12)))
            ipay += [np.round(utils.utilities.ipmt(pv,self.interest_rate),2)]
            ppay += [np.round(utils.utilities.ppmt(pv,self.interest_rate,p),2)]
            pay += [ppay[-1]+ipay[-1]]
            period += [i + 1]
            mon += [i % 12 + 1]
            year += [int(np.floor(i/12))+self.start_year]
            time_interp += [int(np.floor(i/12))+self.start_year + i % 12]
            if i < self.term-1:
                value += [np.round(pv-ppay[-1]-epay[i],2)]
        pmipay = [0 for i in range(self.term)]
        if self.subcategory == 'Mortgage':
            # Interpolate asset_value - should be an exponential interpolation, but whatever...it doesn't make a huge difference
            asset_val_interp = list(np.interp(time_interp,self.cal_year,self.asset_value))
            equity_prop = [1-value[i]/asset_val_interp[i] for i in range(self.term)]
            #pmi_thresh = (1-self.pmi_thresh_pct)*self.principal
            pmi = self.pmi_rate*self.principal/12
            pmipay = [pmi if equity_prop[i] > self.pmi_thresh_pct else 0 for i in range(self.term)]
            pay = [pay[i]+pmipay[i] for i in range(self.term)]
        tpay = [pay[i]+epay[i] for i in range(self.term)]
        amortization_table = pd.DataFrame({'year':year,'month':mon,'period':period,
                                           'value':value,'principal_payment':ppay,
                                           'interest_payment':ipay,'pmi':pmipay,'payment':pay,'extra_payment':epay,'total_payment':tpay},index=period)
        
        self.amortization_table = amortization_table
        payoff_ind = min(self.amortization_table.index[self.amortization_table['year']==self.end_year],
                         default=max(self.amortization_table.index))
        amortization_table.loc[payoff_ind:,:] = 0
        # if 'payoff_year' in self.__dict__:
        #     payoff_ind = min(self.amortization_table.index[self.amortization_table['year']==self.payoff_year])
        #     amortization_table.loc[payoff_ind:,:] = 0
        
        self.extra_payment = list(self.amortization_table['extra_payment'])
        return(self)
    
    def annualize_amort(self):
        """Convert monthly amortization to annual totals."""
        self = self.amortize()
        amort_annual = self.amortization_table.pivot_table(index=['year'],
                                                           values=['value','payment','principal_payment','interest_payment','pmi','extra_payment','total_payment'],
                                                           aggfunc={'payment':'sum','principal_payment':'sum','interest_payment':'sum','pmi':'sum','extra_payment':'sum','total_payment':'sum','value':'max'})
        amort_annual = amort_annual.reset_index(drop=False)
        amort_annual = amort_annual.to_dict('series')
        amort_annual = pd.DataFrame({key:list(amort_annual[key]) for key in amort_annual})
        amort_annual.index = amort_annual['year']
        amort_annual = amort_annual.rename(columns={key:(key+'_annual') for key in amort_annual.columns if key != 'value'})

        self.cal_year = pd.Series(amort_annual.index)
        for col in amort_annual.columns:
            setattr(self,col,amort_annual[col].astype(int))

        return(self)
    
    def update(self):
        """Update expense values and components."""
        return(self.annualize_amort())
    
    def make_expense_obj(self,plan):
        """Create related expense objects for liability payments."""
        self.dependent_objs = True
        #
        paired = [x for x in plan.pairs['series'] if x[0]==self.id]
        subcat = self.subcategory
        for pair in paired:
            if pair[1].split('_')[0] == 'Asset':
                subcat = plan.get_object_from_id(pair[1]).name
                
        exp_obj = ExpenseObj(self.person,'Necessary',subcat,self.name,'',self.cal_year,self.total_payment_annual,
                             True,False,{'start_year':self.start_year,'end_year':self.end_year})
        
        # Mark as future event object if the parent liability is a future event
        if self.future_event:
            exp_obj.future_event = True
        
        # Occassionally useful for tax purposes
        exp_obj.interest_payment = self.interest_payment_annual
        
        # Set paired attributes
        exp_obj.paired_attr['series'] |= {self.id:[['payment_annual','value',1.0],['interest_payment_annual','interest_payment',1.0]]}
        exp_obj.paired_attr['time'] |= {self.id:[['start_year','start_year',0],['end_year','end_year',0]]}
        #
        plan.pairs['series'].append([self.id,exp_obj.id])
        plan.pairs['time'].append([self.id,exp_obj.id])

        # Add and Update
        plan.expenses.append(exp_obj)
        plan = exp_obj.project(plan)
        
        if sum(self.extra_payment) > 0:
            extra_exp_obj = ExpenseObj(self.person,'Discretionary',self.category,self.name+' (Extra Payment)','',self.cal_year,self.extra_payment_annual,
                             True,False,{'start_year':self.start_year,'end_year':self.end_year})
            # Mark as future event object if the parent liability is a future event
            if self.future_event:
                extra_exp_obj.future_event = True
            extra_exp_obj.paired_attr['series'] |= {self.id:[['extra_payment_annual','value',1.0]]}
            extra_exp_obj.paired_attr['time'] |= {self.id:[['start_year','start_year',0],['end_year','end_year',0]]}                 
            #
            plan.pairs['series'].append([self.id,extra_exp_obj.id])
            plan.pairs['time'].append([self.id,extra_exp_obj.id])

            # Add and Update
            plan.expenses.append(extra_exp_obj)
            plan = extra_exp_obj.project(plan)

        return(plan)
            

   