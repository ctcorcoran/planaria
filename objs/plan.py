#####################
# CLASS DEFINITIONS #
#####################

import pandas as pd
import json as json
import numpy as np
import plotly.express as px
import copy

# import sys
# sys.path.append('../utils')
import utils.utilities
import objs.financial_objects
import utils.tax_functions
import utils.plotting

# Define a custom encoder for converting int64s
# and other non-serializable np data types:
class NpEncoder(json.JSONEncoder):
    """Custom JSON encoder for NumPy data types."""
    
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Series,pd.DataFrame)):
            return obj.to_dict()
        return json.JSONEncoder.default(self, obj)


# People
# | attr: cal_yr,age ; dependent (logical) ; pet (logical - optional)

class Person:
    """Represents a person in the financial plan."""
    counter = 0
    def __init__(self,name,birth_year,cal_year,dependent,pet=False):
        Person.counter += 1
        
        self.obj_type = 'Person'
        self.id = self.obj_type + '_' + str(Person.counter)
        
        #retirement age, age of death optional
        self.name = name #string
        self.cal_year = cal_year #pd.Series
        self.birth_year = birth_year 
        self.current_age = cal_year[cal_year.index[0]]-birth_year #integer
        self.age = pd.Series([self.current_age+i for i in range(len(cal_year))],index=self.cal_year)
        self.dependent = dependent #logical
        # if self.dependent:
        #     self.age = self.age.loc[self.age < 18]
        #self.pet = pet #perhaps add a pet as a "person" eventually
        
        # Child cost DataFrame for dependents
        self.child_cost_df = None
        
    def standardize_timeseries(self,cal_year):
        """Standardize person's time series to match plan calendar."""
        self.cal_year = cal_year
        self.current_age = cal_year[cal_year.index[0]]-self.birth_year
        self.age = pd.Series([self.current_age+i for i in range(len(cal_year))],index=self.cal_year)
        return(self)
        
    def to_serializable(self):
        """Convert person to JSON-serializable format."""
        out = copy.deepcopy({key:(value.to_dict() if isinstance(value,pd.Series) else value) for key, value in self.__dict__.items()})
        # Handle DataFrame serialization
        if 'child_cost_df' in out and out['child_cost_df'] is not None:
            out['child_cost_df'] = out['child_cost_df'].to_dict()
        return(out)

# Plan 
# | attr: people,income,expenses,assets,liabilities (list of obj);assli_pairs, events (list of ordered pairs);indicators (dict of lists)
# | methods: update_plan,balance_and_tax,income_and_payroll_tax, indicators, to_dataframes?, equalize_timeseries, combine_expenses

# | utility methods: get_object_from_id, get_id_from_name, get_object_from_name 

class Plan:
    """Main container for the entire financial plan."""
    counter = 0
    def __init__(self,name,start_year,n_years,infl_rate,col_rate):
        Plan.counter += 1
        
        self.obj_type = 'Plan'
        self.id = self.obj_type + '_' + str(Plan.counter)
        
        self.name = name
        self.start_year = start_year
        self.n_years = n_years
        self.cal_year = pd.Series([self.start_year + i for i in range(n_years+1)])
        #self.cal_year.index = self.cal_year
        self.infl_rate = infl_rate
        self.col_rate = col_rate
        
        
        #People in Plan
        self.people = []
        
        #List of events, of the form (year,description,id)
        self.events = []

        #Lists for object storage
        self.income = []
        self.expenses = []
        self.assets = []
        self.liabilities = []
        
        #Dict of lists of paired objects
        self.pairs = {'series':[],'time':[],'share':[]}
        
        #List of future events
        self.events = []
        
        #Drawdown order of savings accounts
        self.drawdown_order = {} 
        
        #Marriage
        self.married = pd.Series(False,index=self.cal_year)
        self.marriage_year = None

        # Combine Expenses
        self.combined_expenses = pd.Series(False,index=self.cal_year)
        self.combine_year = None
        self.expense_share = 'Even'
        
        # Children
        self.dependents = pd.Series(0,index=self.cal_year)

    def reorder_object_ids(self):
        """Reorder object IDs for consistency and serialization."""
        replace_dict = {}
        for lst in ['income','expenses','assets','liabilities']:
            def sort_key(obj):
                value = obj.value
                if isinstance(value, pd.Series):
                    if obj.start_year in value.index:
                        return value[obj.start_year]
                    if len(value) > 0:
                        return value.iloc[0]
                    return 0
                return value
            setattr(self,lst,sorted(getattr(self,lst),key=sort_key, reverse=True))
            replace_dict |= {obj.id:(obj.id.split('_')[0]+'_'+str(getattr(self,lst).index(obj)+1)) for obj in getattr(self,lst)}
        for obj in self.income+self.expenses+self.assets+self.liabilities:
            # Update ID, paired attributes, and downpayment (if relevant)
            obj.id = replace_dict[obj.id]
            obj.paired_attr = {key_:{replace_dict[key]:val for key, val in obj.paired_attr[key_].items()} for key_ in ['series','time','share']}
            if 'down_payment_sources' in self.__dict__.keys():
                self.down_payment_sources['id'] = self.down_payment_sources['id'].apply(lambda x: replace_dict[x]) 
            
        # Change external lists: pairs, events, drawdown order   
        self.pairs = {key:[[replace_dict[pair[0]],replace_dict[pair[1]]] for pair in self.pairs[key]] for key in ['series','time','share']}
        self.drawdown_order = {key:[replace_dict[obj_id] for obj_id in val] for key, val in self.drawdown_order.items()}
        updated_events = []
        for year, label, payload in self.events:
            # Update payload if it's an object ID or a dict containing IDs
            if isinstance(payload, dict):
                payload = copy.deepcopy(payload)
                if 'sources' in payload:
                    payload['sources'] = [(replace_dict.get(src, src), prop) for src, prop in payload['sources']]
                updated_events.append([year, label, payload])
            else:
                updated_events.append([year, label, replace_dict.get(payload, payload)])
        self.events = updated_events
        
        return(self)
    
    def to_json_string(self):
        """Convert plan to JSON string for saving."""
        temp = copy.deepcopy(self)
        temp = temp.reorder_object_ids()
        for key in temp.__dict__:
            if isinstance(temp.__dict__[key],pd.Series):
                temp.__dict__[key] = temp.__dict__[key].to_dict()
            if key in ['people','income','expenses','assets','liabilities']:
                temp.__dict__[key] = [obj.to_serializable() for obj in temp.__dict__[key]]
        return(json.dumps(temp.__dict__,cls=NpEncoder))

    #Error handling needed here
        
    def get_id_from_name(self,obj_type,name,person=None):
        if obj_type == 'Person':
            return(next((obj.id for obj in self.people if ((obj.obj_type == obj_type)&(obj.name == name))), None))
        else:
            objects = [obj for obj in self.income+self.expenses+self.assets+self.liabilities if ((obj.obj_type == obj_type)&(obj.name == name))]
            
            # if multiple objects and person
            if len(objects) == 0:
                #print('No objects found')
                return(None)
            elif len(objects) == 1:
                if person == None:
                    return(objects[0].id)
                else:
                    if objects[0].person != person:
                        print('Object found, but with different person')
                        return(None)
                    else:
                        return(objects[0].id)
            else:
                if person == None:
                    print('Multiple objects found, please specify person')
                    return(None)
                elif person not in [obj.person for obj in objects]:
                    print('Multiple objects found, none with specified person')
                    return(None)
                else:
                    return(next(iter([obj.id for obj in objects if obj.person == person])))
                

    def get_object_from_id(self,ID):
        """Get object by ID from any object list."""
        return(next((obj for obj in self.people+self.income+self.expenses+self.assets+self.liabilities if obj.id == ID), None))

    def get_object_from_name(self,obj_type,name,person=None):
        obj_id = self.get_id_from_name(obj_type,name,person)
        if obj_id == None:
            return(None)
        else:
            return(self.get_object_from_id(obj_id))
        # Maybe a try-except statement here...

    def remove_object_by_id(self,ID):
        """Remove object and all its dependencies from the plan."""
        # Translate id prefix to plan attribute
        type_dict = {'Person':'people','Expense':'expenses','Liability':'liabilities','Income':'income','Asset':'assets'}
        
        # Get ids in the plan attribute containing ID
        lst = type_dict[ID.split('_')[0]]
        id_list = [obj.id for obj in getattr(self,lst)]
        
        # Get parents and children
        parent_ids = list(set([pair[0] for pair_list in self.pairs.values() for pair in pair_list if pair[1]==ID]))
        child_ids = list(set([pair[1] for pair_list in self.pairs.values() for pair in pair_list if pair[0]==ID]))
        
        # Break links with children, remove if necessary
        for child_id in child_ids:
            child = self.get_object_from_id(child_id)
            child.paired_attr = {key:{key_:pair_list for key_, pair_list in child.paired_attr[key].items() if key_ != ID} for key in child.paired_attr.keys()}
            if len(child.paired_attr['series']) + len(child.paired_attr['time']) == 0:
                self = self.remove_object_by_id(child_id)
        
        # Remove from plan.pairs
        self.pairs = {key:[pair for pair in self.pairs[key] if ID not in pair] for key in self.pairs.keys()}
        
        # If any parents are no longer in pairs, set dependent_objs to false:
        for parent_id in parent_ids:
            if parent_id not in set([pair[0] for pair_list in self.pairs.values() for pair in pair_list]):
                self.get_object_from_id(parent_id).dependent_objs = False
        
        # Remove object, and remove from drawdown order just in case
        del getattr(self,lst)[id_list.index(ID)]
        self.drawdown_order = {person:[x for x in lst if x != ID] for person, lst in self.drawdown_order.items()}
        
        return(self)
    
    def project_all(self):
        """Project all objects in the plan forward through time."""
        for obj in self.income+self.expenses+self.liabilities+self.assets:
            self = obj.project(self)
        return(self)
    
    def get_tax_keyword_objects(self,tax_keyword):
        if isinstance(tax_keyword,str):
            return([obj for obj in self.expenses if obj.tax_keyword == tax_keyword])
        elif isinstance(tax_keyword,list):
            return([obj for obj in self.expenses if (obj.tax_keyword in tax_keyword)])

    def standardize_all_series(self):
        """Standardize all time series to match plan calendar."""
        ## ADD PLAN ATTRIBUTE SERIES: Marriage (Logical), Combined_Expenses (Logical), Dependents (Integer) 
        for obj in self.people+self.income+self.expenses+self.assets+self.liabilities:
            obj = obj.standardize_timeseries(self.cal_year)
        return(self)
        
    def aggregate(self,obj_type,person='Joint'):
        """Aggregate objects by type and person."""
        self.standardize_all_series()
        if person == 'Joint':
            people = [person.id for person in self.people if person.dependent==False] +['Joint']
        else:
            people = [person,'Joint']
        if obj_type == "Expense":
            # print('Aggregating '+person)
            temp = [obj for obj in self.expenses if obj.person in people]
            agg = pd.Series(0,index=self.cal_year)
            for person_ in people:
                if person_ != 'Joint':
                    # if person_ == 'Person_1':
                    #     print([(obj.name,obj.components[person_][2024]) for obj in temp if person_ in obj.components.keys()])
                    agg += sum([obj.components[person_] for obj in temp if person_ in obj.components.keys()])
        else:
            if obj_type == "Asset":
                temp = self.assets
            elif obj_type == "Liability":
                temp = self.liabilities
            elif obj_type == 'Income':
                temp = self.income
            agg = sum([obj.value for obj in temp if obj.person in people])
        return(agg)
        
    ### Computational Methods
    def get_married(self,year):
        """Set marriage status and apply marriage-related changes."""
        self.marriage_year = year
        self.married = pd.Series([True if yr >= year else False for yr in self.cal_year],index=self.cal_year)
        return(self)
    
    def generate_expense_share(self):
        adults = [person.id for person in self.people if person.dependent == False]
        if(self.expense_share == 'Proportional'):
            #self.props_input = True
            all_income = [obj.id for obj in self.income if (obj.person in adults) and (obj.category == 'Earned')]
            inc_dict = {}
            for inc_id in all_income:
                temp = self.get_object_from_id(inc_id)
                inc_dict |= {temp.person:temp.value}
            self.share_props = sum([inc_dict[person] for person in inc_dict.keys() if person == 'Person_1'])/sum(inc_dict.values())
        else:
            self.share_props = pd.Series(0.5,index=self.cal_year)
        return(self)
    
    def drawdown(self,amt,year,person,keyword=None):
        """Draw down from assets in specified order when expenses exceed income."""
        # drawdown amt is ALWAYS negative, which means positive values are passed to 
        # asset.contribution. Instead, we are always making withdrawals in this function, and 
        # thus operate through transaction (unless I add a 'withdrawal' component when I componentize
        # assets. 
    
        if amt >= 0:
            print('Drawdown must be negative')
        else:
            # 
            amt_remaining = amt
            counter = 0
            while amt_remaining > 0:
                acct_id = self.drawdown_order[person][counter]
                if acct_id.split('_')[0] == 'Liab':
                    sign = 1
                    keyword = 'charges'
                    # will need to fix below if credit cards are added
                else:
                    sign = -1
                    if keyword == None:
                        keyword = 'contribution'
                acct_val = self.get_object_from_id(acct_id).value[year]
                if amt_remaining >= acct_val:
                    getattr(self.get_object_from_id(acct_id),keyword)[year] = sign*acct_val
                    amt_remaining -= acct_val
                    counter += 1
                else:
                    getattr(self.get_object_from_id(acct_id),keyword)[year] = sign*amt_remaining
                    amt_remaining = 0
                self = self.get_object_from_id(acct_id).project(self)
        return(self)
    
    def combine_expense(self,obj_name,comb_year):
        if len(self.people) == 1:
            return(self)
        else:
            expenses = [obj for obj in self.expenses if obj.name == obj_name]
            exp_ids = [obj.id for obj in expenses]
            
            # Check if the interesection of the events and exp_ids is empty
            # If empty, combine. If not empty, adjust start_year and project,
            # triggering a combination 
            
            if 'Joint' in [obj.person for obj in expenses]:
                obj_id = self.get_object_from_name('Expense', obj_name,'Joint').id
                # Clean up any global pairs that referenced the prior joint expense
                self.pairs = {k:[pair for pair in self.pairs[k] if obj_id not in pair] for k in self.pairs.keys()}
                # Remove the joint expense from working list and plan storage
                expenses = [obj for obj in expenses if obj.id != obj_id]
                self.expenses = [obj for obj in self.expenses if obj.id != obj_id]
                
            if len(expenses) > 0:
                # Sum indexed series of values for the combined objects, prune it
                # to the combination year, the reexpand
                for obj in expenses:
                    obj.dependent_objs = True
                    obj.end_year = comb_year-1
                    self = obj.project(self)
                    
                # Create New Expense
                new_joint_expense = objs.financial_objects.ExpenseObj('Joint',expenses[0].category,expenses[0].subcategory,obj_name,
                                               expenses[0].tax_keyword,self.cal_year,
                                               0, #combined_val,
                                               expenses[0].fixed,
                                               False, #expenses[0].editable,
                                               {'props_input':True,'props':1.0,'start_year':comb_year,'infl_rate':self.infl_rate})
                new_joint_expense.paired_attr['series'] |= {obj.id:[['value_input','value_input',1.0]] for obj in expenses}
                new_joint_expense.paired_attr['time'] |= {obj.id:[['end_year','start_year',1]] for obj in expenses}
                
                self.pairs['series'] += [[obj.id,new_joint_expense.id] for obj in expenses]
                self.pairs['time'] += [[obj.id,new_joint_expense.id] for obj in expenses]
                
                self.expenses.append(new_joint_expense)
                self = new_joint_expense.project(self)     
        
        return(self)

    def combine_expenses(self,obj_name_list,comb_year):
        for obj_name in obj_name_list:
            self = self.combine_expense(obj_name,comb_year)
        return(self)
    
    def uncombine_expense(self,obj_name):
        """Reverse a prior combination for a single expense name.
        Restores predecessor expenses to full duration and removes the joint expense and links.
        """
        if len(self.people) == 1:
            return self
        # Find the joint expense for this name (avoid noisy get_object_from_name messages)
        joint_obj = next((obj for obj in self.expenses if obj.obj_type == 'Expense' and obj.name == obj_name and obj.person == 'Joint'), None)
        if joint_obj is None:
            return self
        # Collect predecessor ids from the joint's paired attributes
        predecessor_ids = []
        for key in ['series','time','share']:
            if key in joint_obj.paired_attr:
                predecessor_ids += list(joint_obj.paired_attr[key].keys())
        # For each predecessor, remove pairings to the joint and restore end_year
        for pred_id in predecessor_ids:
            pred = self.get_object_from_id(pred_id)
            if pred is None:
                continue
            # Remove references to the joint from predecessor's paired_attr
            pred.paired_attr = {k:{pid:plist for pid, plist in pred.paired_attr[k].items() if pid != joint_obj.id} for k in pred.paired_attr.keys()}
            # Restore full duration
            pred.end_year = int(max(pred.cal_year))
            # Reproject predecessor
            self = pred.project(self)
        # Remove global pairs that include the joint
        self.pairs = {k:[pair for pair in self.pairs[k] if joint_obj.id not in pair] for k in self.pairs.keys()}
        # Remove the joint expense itself
        self.expenses = [exp for exp in self.expenses if exp.id != joint_obj.id]
        return self

    def uncombine_expenses(self,obj_name_list):
        for name in obj_name_list:
            self = self.uncombine_expense(name)
        return self
                
                
    def calculate_income_and_payroll_tax(self):
        # returns a tax_df_dict
        
        self.tax_df_dict = utils.tax_functions.calculate_income_and_payroll_tax(self)
        return(self)

    def balance_and_tax(self):
        """Calculate taxes and balance income vs expenses."""
        self = self.calculate_income_and_payroll_tax()
        self = utils.tax_functions.balance_and_tax(self)
        return(self)
    
    ### Plotting Methods
    
    # Some are fully described methods for simple plots such as pie charts
    # Others are wrappers for more complex plotting functions stored elsewhere
    def pie_chart(self,obj_type,year,plot_type='pie',include_events=False,cats_to_ignore=[],person=None):
        color_dict = (utils.plotting.CASHFLOW_COLORS | {
            'Retirement':'cornflowerblue','Bonds':'cornflowerblue','Real Estate':'gold','Automobile':'gold',
            'Revolving':'darkorange','Installment':'gold'
        })
        
        # Don't include future events, or ignored categories
        if include_events == False:
            objs = [obj for obj in getattr(self,obj_type) if obj.category not in cats_to_ignore and not obj.future_event]
        else:
            objs = [obj for obj in getattr(self,obj_type) if obj.category not in cats_to_ignore]

        if person is not None:
            people = utils.plotting.make_people_list(self, person) + ['Joint']
            objs = [obj for obj in objs if obj.person in people]
            
        plot_df = pd.DataFrame({'name':[obj.name for obj in objs],
                                'person':['Joint' if obj.person == 'Joint' else self.get_object_from_id(obj.person).name for obj in objs],
                                'category':[obj.subcategory if obj.obj_type == 'Asset' else obj.category for obj in objs],
                                'value':[obj.value[year] for obj in objs],
                                'label':[obj.name + ' (Joint)' if obj.person == 'Joint' else obj.name + ' (' + self.get_object_from_id(obj.person).name + ')' for obj in objs]})
        if plot_type == 'pie':
            fig = px.pie(plot_df,values='value',names='label',color='category',
                         color_discrete_map=color_dict,hole=0.33)
            fig.update_traces(textposition='inside', textinfo='label+value')
            fig.update(layout_showlegend=False)
        elif plot_type == 'sunburst':
            fig = px.sunburst(plot_df,values='value',path=['category','label'],color='category',
                         color_discrete_map=color_dict)
            fig.update_traces(textinfo="label+percent root")
        return(fig)
    
    def expense_plots(self,person,level,after_tax=False):
        return(utils.plotting.expense_plots(self,person,level,after_tax))
    
    def asset_plots(self,person,level,net_worth_formula=2):
        return(utils.plotting.asset_plots(self,person,level,net_worth_formula))
    
    def cashflow_sankey(self,person,year,comb_all_exp=False,normalize=False):
        return(utils.plotting.cashflow_sankey(self,person,year,comb_all_exp,normalize))
    
    def ratio_plot(self,person,names):
        if 'analytical_timeseries' not in self.__dict__.keys():
            print('Must Update Plan First...')
            return()
        else:
            df = self.analytical_timeseries.loc[self.analytical_timeseries['person']==person,:]
            return(utils.plotting.ratio_plot(df,names))