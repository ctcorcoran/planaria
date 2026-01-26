import pandas as pd
import numpy as np
import json
from copy import deepcopy

import utils.utilities
import objs.financial_objects
import utils.plotting

#### SUMMING A LIST OF PANDAS SERIES????

# LOAD TAX PARAMETERS

fed_file_path = 'data/fed_tax_values.json'

with open(fed_file_path, 'r') as j:
    try:
        fed = json.loads(j.read())
    except json.decoder.JSONDecodeError as e:
        print(f"Invalid JSON string: {e}")

state_file_path = 'data/state_tax_values.json'

with open(state_file_path, 'r') as j:
    try:
        state = json.loads(j.read())['California']
    except json.decoder.JSONDecodeError as e:
        print(f"Invalid JSON string: {e}")

noninflationary = ['age','rate','rates','multiplier','multipliers']

# Convert string 'np.inf' to numpy infinity object

def replace_npinf(obj):
    """Replace numpy infinity values with large numbers for tax calculations."""
    if isinstance(obj,dict):
        for key in obj.keys():
            obj[key] = replace_npinf(obj[key])
    elif isinstance(obj,str):
        if obj == "np.inf":
            obj = np.inf
    elif isinstance(obj,list):
        obj = [replace_npinf(item) for item in obj]
    return(obj)
            
fed = replace_npinf(fed)
state = replace_npinf(state)
        

#################
# TAX FUNCTIONS #
#################

# apply tax in a single year 

def apply_tax(income,tax_brackets,tax_rate):
  """Apply progressive tax calculation to income."""
  i=0
  tax = 0
  while tax_brackets[i] < income:
    if i==0:
      tax += tax_brackets[i]*tax_rate[i]
    else:
      tax += (tax_brackets[i]-tax_brackets[i-1])*tax_rate[i]
    i += 1
  tax += max(0,(income-tax_brackets[i-1])*tax_rate[i])
  return(tax)

# apply apply_tax

def apply_tax_series(income_series,tax_bracket_series,tax_rate_series):
  """Apply tax calculation to time series of income."""
  return(pd.Series([apply_tax(income_series[year],tax_bracket_series[year],tax_rate_series[year]) for year in income_series.index],index=income_series.index))

# calculate_income_and_payroll_tax

def calculate_income_and_payroll_tax(plan):
  """
  Calculate income and payroll taxes for all filing scenarios.
  
  Args:
      plan: The plan object containing income and people
      
  Returns:
      Dictionary of tax calculations for different filing statuses
  """
  people = [person.id for person in plan.people if person.dependent==False]
  if len(people) == 1:
    filing_status_list = ['single']
  elif len(people) == 2:
    filing_status_list = ['single','joint','separate']  
  
  tax_df_dict = {status:{} for status in filing_status_list} 
  
  # For ease of navigating the dict, we will recalculate from in the input year for each
  # Year in the projection. There is probably a faster way to do this by not looping over time, but
  # that is a task for another day...
  
  fed_infl = deepcopy(fed)
  state_infl = deepcopy(state)
  for tax_vals in [fed_infl,state_infl]:
      for level in ["tax","deductions","credits"]:
          for name in tax_vals[level]:
              if isinstance(tax_vals[level][name],dict) == False:
                  tax_vals[level][name] = {filing_status:tax_vals[level][name] for filing_status in ["single","joint","separate"]}
              if "separate" not in tax_vals[level][name]:
                  tax_vals[level][name]["separate"] = tax_vals[level][name]["single"]
              if name.split('_')[-1] in noninflationary:
                  tax_vals[level][name] = {filing_status:pd.Series([tax_vals[level][name][filing_status] for _ in plan.cal_year],index=plan.cal_year) for filing_status in tax_vals[level][name]}
              else:
                  tax_vals[level][name] = {filing_status:utils.utilities.inflate_amount(tax_vals[level][name][filing_status],utils.utilities.expand_contract(plan.infl_rate,plan.cal_year)) for filing_status in tax_vals[level][name]}
                  
  for tax_filing in filing_status_list:
    if tax_filing == 'joint': 
      joint_exp_multi = 1
      filer_list = [people + ['Joint']] 
    elif tax_filing == 'separate' or tax_filing == 'single': 
      joint_exp_multi = 0.5
      filer_list = [[name,'Joint'] for name in people]
  
    for filers in filer_list:
      # Gross Taxable Income
      gross_taxable_income = sum([obj.value for obj in plan.income if ((obj.taxable==True) and (obj.person in filers))])
      if isinstance(gross_taxable_income,(float,int)):
          if gross_taxable_income == 0:
              gross_taxable_income = pd.Series(0,index=plan.cal_year)
      # ABOVE - THE - LINE DEDUCTIONS
      # Retirment / HSA Accounts:
      # Cannot be jointly held, and thus have individual limits (which have already been enforced)    
       
      pretax_deductions = sum([obj.value for obj in plan.get_tax_keyword_objects(['Traditional','HSA']) if (obj.person in filers)])
  
      # Modifed Adjusted Gross Income (MAGI)
      modified_adjusted_gross_income = gross_taxable_income - pretax_deductions
  
      # Student Loan Interest Deduction
      # Phases out at higher incomes...haven't bothered with this yet
      
      student_loan_interest = sum([obj.interest_payment_annual for obj in plan.get_tax_keyword_objects("Student Loan") if (obj.person in filers)])
      if isinstance(student_loan_interest,int):
          if student_loan_interest == 0:
              student_loan_interest = pd.Series([0 for _ in range(len(plan.cal_year))],index=plan.cal_year)
          else:
              print('Error - Summing Student Loan Interest')
      else:
         student_loan_interest = pd.concat([student_loan_interest,fed_infl['deductions']['student_loan_max'][tax_filing]], axis=1).min(axis=1) 
         student_loan_interest[fed_infl['deductions']['student_loan_magi_thresh'] <= modified_adjusted_gross_income] = 0
  
      # Adjusted Gross Income (AGI)
      adjusted_gross_income = modified_adjusted_gross_income-student_loan_interest
      
      ### BELOW - THE - LINE DEDUCTIONS
      # One difficulty with this is the SALT itemized deduction requires requires the computation of 
      # state taxes before it can be determined whether or not to itemize for federal...can this be correct?
      
      #Itemized Deductions (common)
      fed_itemized_deductions = []
      state_itemized_deductions = []
  
      # Mortgage interest on up to two homes, and points
      # Will need to look at this for multiple houses, when figuring deductible interest is much trickier
      if len([obj for obj in plan.get_tax_keyword_objects('Mortgage') if obj.person in filers]) > 0:
        mortgage_rate = plan.get_tax_keyword_objects('Mortgage')[0].interest_rate
        mortgage_interest = sum([obj.interest_payment_annual*joint_exp_multi if obj.person=='Joint' else obj.interest_payment_annual for obj in plan.get_tax_keyword_objects('Mortgage')]) #trivial sum
        #
        fed_itemized_deductions.append(pd.concat([mortgage_interest,fed_infl['deductions']['mortgage_limit'][tax_filing]*mortgage_rate], axis=1).min(axis=1))
        state_itemized_deductions.append(pd.concat([mortgage_interest,state_infl['deductions']['mortgage_limit'][tax_filing]*mortgage_rate], axis=1).min(axis=1))
      
      # Property taxes inf state limit, 10k federal limit (combined with state taxes)
      if len([obj for obj in plan.get_tax_keyword_objects('Property Tax') if obj.person in filers]) > 0:
        property_tax = plan.get_tax_keyword_objects('Property Tax')[0].value
        if plan.get_tax_keyword_objects('Property Tax')[0].person=='Joint':
            property_tax = property_tax*joint_exp_multi
        state_itemized_deductions.append(pd.concat([property_tax,state_infl['deductions']['property_tax_max'][tax_filing]], axis=1).min(axis=1))
      else:
        property_tax = pd.Series([0 for _ in plan.cal_year],index=plan.cal_year) #Makes calculating SALT easier
  
      # Medical and dental expenses that exceed 7.5% of your adjusted gross income,
      if len([obj for obj in plan.get_tax_keyword_objects('Medical') if obj.person in filers]) > 0:
        medical_expenses = [obj for obj in plan.get_tax_keyword_objects("Medical") if obj.person in filers]
        medical_expenses = sum([obj.value*joint_exp_multi if obj.person=='Joint' else obj.value for obj in medical_expenses])
        #
        fed_itemized_deductions.append(pd.concat([medical_expenses,adjusted_gross_income*fed_infl['deductions']['medical_limit_rate']], axis=1).min(axis=1))
        state_itemized_deductions.append(pd.concat([medical_expenses,adjusted_gross_income*state_infl['deductions']['medical_limit_rate']], axis=1).min(axis=1))
  
      # Charitable donations 
      if len([obj for obj in plan.get_tax_keyword_objects('Charitable Donations') if obj.person in filers]) > 0:
        charitable_donations = [obj for obj in plan.get_tax_keyword_objects("Charitable Donations") if obj.person in filers]
        charitable_donations = sum([obj.value*joint_exp_multi if obj.person=='Joint' else obj.value for obj in charitable_donations])
        #
        fed_itemized_deductions.append(pd.concat([charitable_donations,adjusted_gross_income*fed_infl['deductions']['charity_limit_rate']], axis=1).min(axis=1))
        state_itemized_deductions.append(pd.concat([charitable_donations,adjusted_gross_income*state_infl['deductions']['charity_limit_rate']], axis=1).min(axis=1))
  
      # State and Local income or sales Taxes (SALT - Federal Only)
      # Since state income tax may be deductible, we compute it here...which is annoying
      # I could alternatively use withholding, but it's not an easy formula
      
      if len(state_itemized_deductions)==0:
        state_itemized_deductions = pd.Series([0 for _ in plan.cal_year],index=plan.cal_year)
      elif len(state_itemized_deductions) > 0:
        state_itemized_deductions = sum(state_itemized_deductions)
      state_itemized_deductions = pd.concat([state_itemized_deductions,pd.Series(['Itemized' for _ in plan.cal_year],index=plan.cal_year)],axis=1).rename(columns={0:'amt',1:'name'})
      state_standard_deduction = pd.concat([state_infl['deductions']['standard_deduction'][tax_filing],pd.Series(['Standard' for _ in plan.cal_year],index=plan.cal_year)],axis=1).rename(columns={0:'amt',1:'name'})  
      all_state_deductions = pd.concat([state_standard_deduction,state_itemized_deductions]).reset_index(drop=False)
      state_deduction = all_state_deductions.groupby("index").agg({'amt':['idxmax','max']}).droplevel(0,axis=1).merge(all_state_deductions[['index','name']],left_on='idxmax',right_index=True).drop(['idxmax','index'],axis=1).rename(columns={'max':'amt'})
      state_taxable_income = adjusted_gross_income-state_deduction["amt"]
      state_taxable_income = state_taxable_income.apply(lambda x: max(x,0))
      state_income_tax = apply_tax_series(state_taxable_income,state_infl['tax']['brackets'][tax_filing],state_infl['tax']['rates'][tax_filing])
      
      
      # Apply Any Tax Credits... Childcare Tax Credit is the only CA one I see as relevant right now
      state_tax_credits = []
      fed_tax_credits = []
  
      # Child and Dependent Care Credit 
      if (tax_filing != 'separate') & len([obj for obj in plan.get_tax_keyword_objects('Child or Dependent Care') if obj.person in filers]) > 0:
        child_dependent_care_expenses = [obj for obj in plan.get_tax_keyword_objects('Child or Dependent Care') if obj.person in filers]
        child_dependent_care_expenses = sum([obj.value*joint_exp_multi if obj.person=='Joint' else obj.value for obj in child_dependent_care_expenses])
        qualifying_dependents = [[1 if ((age < 13) and (age >= 0)) else 0 for age in person.age] for person in plan.people if person.dependent == True]
        qualifying_dependents = pd.Series([sum(x) for x in zip(*qualifying_dependents)],index=plan.cal_year)

        fed_child_dependent_care_eff_multi = pd.Series([fed_infl['credits']['child_dep_care_multipliers'][tax_filing][i][list(lim >= adjusted_gross_income[i] for lim in fed_infl['credits']['child_dep_care_limits'][tax_filing][i]).index(True)] for i in plan.cal_year],index=plan.cal_year)
        fed_child_dependent_care_amt = fed_child_dependent_care_eff_multi*child_dependent_care_expenses
        fed_child_dependent_care_eff_max = pd.Series([fed_infl['credits']['child_dep_care_max'][tax_filing][i][0] if qualifying_dependents[i] == 1 else 0 if qualifying_dependents[i] == 0 else fed_infl['credits']['child_dep_care_max'][tax_filing][i][1] for i in plan.cal_year],index=plan.cal_year)
        fed_child_dependent_care_credit = pd.concat([fed_child_dependent_care_amt,fed_child_dependent_care_eff_max], axis=1).min(axis=1) 
        fed_tax_credits.append(fed_child_dependent_care_credit)
        
        # State credit currently based off federal for parsimony...
        state_child_dependent_care_eff_multi = pd.Series([state_infl['credits']['child_dep_care_multipliers'][tax_filing][i][list(lim >= adjusted_gross_income[i] for lim in state_infl['credits']['child_dep_care_limits'][tax_filing][i]).index(True)] for i in plan.cal_year],index=plan.cal_year)
        state_child_dependent_care_amt = state_child_dependent_care_eff_multi*child_dependent_care_expenses
        state_child_dependent_care_eff_max = pd.Series([state_infl['credits']['child_dep_care_max'][tax_filing][i][0] if qualifying_dependents[i] == 1 else 0 if qualifying_dependents[i] == 0 else state_infl['credits']['child_dep_care_max'][tax_filing][i][1] for i in plan.cal_year],index=plan.cal_year)
        state_child_dependent_care_credit = pd.concat([state_child_dependent_care_amt,state_child_dependent_care_eff_max], axis=1).min(axis=1) 
        state_tax_credits.append(state_child_dependent_care_credit)
     
      # CA Exemption:
      state_tax_credits.append(state_infl['credits']['exemption'][tax_filing])    
       
      # CA has a child tax credit, but must qualify for earned income tax credit
      # Total state credits and compute tax 
      if len(state_tax_credits)==0:
          state_tax_credits.append(pd.Series([0 for _ in plan.cal_year],index=plan.cal_year))
      
      state_tax_credits = sum(state_tax_credits)
      state_income_tax = state_income_tax - state_tax_credits
      # Currently no excess credit is returned:
      state_income_tax = state_income_tax.apply(lambda x: max(x,0))
      
      # Back to Federal...
      # SALT (State and Local Tax) Deduction
      SALT = pd.concat([fed_infl['deductions']['SALT_max'][tax_filing],(state_income_tax+property_tax)], axis=1).min(axis=1) 
      fed_itemized_deductions.append(SALT)
  
      # Compute federal deduction:

      if len(fed_itemized_deductions)==0:
        fed_itemized_deductions = pd.Series([0 for _ in plan.cal_year],index=plan.cal_year)
      elif len(fed_itemized_deductions) > 0:
        fed_itemized_deductions = sum(fed_itemized_deductions)
      fed_itemized_deductions = pd.concat([fed_itemized_deductions,pd.Series(['Itemized' for _ in plan.cal_year],index=plan.cal_year)],axis=1).rename(columns={0:'amt',1:'name'})
      fed_standard_deduction = pd.concat([fed_infl['deductions']['standard_deduction'][tax_filing],pd.Series(['Standard' for _ in plan.cal_year],index=plan.cal_year)],axis=1).rename(columns={0:'amt',1:'name'})  
      # print(fed_standard_deduction)
      all_fed_deductions = pd.concat([fed_standard_deduction,fed_itemized_deductions]).reset_index(drop=False)
      fed_deduction = all_fed_deductions.groupby("index").agg({'amt':['idxmax','max']}).droplevel(0,axis=1).merge(all_fed_deductions[['index','name']],left_on='idxmax',right_index=True).drop(['idxmax','index'],axis=1).rename(columns={'max':'amt'})
      fed_taxable_income = adjusted_gross_income-fed_deduction["amt"]
      fed_taxable_income = fed_taxable_income.apply(lambda x: max(x,0))
      fed_income_tax = apply_tax_series(fed_taxable_income,fed_infl['tax']['brackets'][tax_filing],fed_infl['tax']['rates'][tax_filing])
      
      
      # Any Federal Tax credits - Childcare and Dependent Care Has Been Handled Above
      # Child Tax credit
      # This is partially refundable as of 2024, but it's complicated and frankly unlikely that we would need it
      #qualifying_children = [[1 if ((age < 18) and (age >= 0)) else 0 for age in person.age] for person in plan.people if person.dependent == True]
      #qualifying_children = pd.Series([sum(x) for x in zip(*qualifying_children)],index=plan.cal_year)
      qualifying_children = plan.dependents
      child_credit_max = qualifying_children*fed_infl['credits']['child_max'][tax_filing]*joint_exp_multi
      child_credit = pd.DataFrame({'I':modified_adjusted_gross_income,'M':child_credit_max,'L':fed_infl['credits']['child_limit'][tax_filing],'R':fed_infl['credits']['child_phaseout_rate'][tax_filing]})
      child_credit = child_credit.apply(lambda x : x.M if x.I <= x.L else x.M - x.R*(x.I-x.L) if x.L < x.I <= x.L + (1/x.R)*x.M else 0,axis=1)   
      fed_tax_credits.append(child_credit)

      # Lifelong Learning Credit
  
      # ---- Not as Applicable
      # Savers Credit, American Opportunity Credit, Earned Income Tax Credit
  
      if len(fed_tax_credits)==0:
        fed_tax_credits.append(pd.Series([0 for _ in plan.cal_year],index=plan.cal_year))
      
      fed_tax_credits = sum(fed_tax_credits)
      fed_income_tax = fed_income_tax - fed_tax_credits
      #
      # Currently, no excess tax credits are returned, though this should be cheked
      fed_income_tax = fed_income_tax.apply(lambda x: max(x,0))
  
      # COMPUTE TOTAL INCOME TAX
      income_tax = fed_income_tax+state_income_tax
  
      # SOCIAL SECURITY AND MEDICARE TAXES (PAYROLL TAXES)
      # SS & MED Income (Only Health Insurance Premiums Deducted Right Now)
      if len([obj for obj in plan.get_tax_keyword_objects('Health Insurance') if obj.person in filers]) > 0:
        ssm_pretax_deductions = [obj for obj in plan.get_tax_keyword_objects("Health Insurance") if obj.person in filers]
        ssm_pretax_deductions = sum([obj.value*joint_exp_multi if obj.person=='Joint' else obj.value for obj in ssm_pretax_deductions])
      else:
        ssm_pretax_deductions = pd.Series([0 for _ in plan.cal_year],index=plan.cal_year)
      ssm_income = gross_taxable_income-ssm_pretax_deductions
  
      # Soc. Security
      ss_tax = ssm_income*fed_infl['tax']['social_security_rate'][tax_filing]
  
      # Medicare
      medicare_tax = ssm_income*fed_infl['tax']['medicare_rate'][tax_filing]

      # Totals
      payroll_tax = ss_tax + medicare_tax
      total_tax = income_tax + payroll_tax
  
      ########  
  
      #Make a Summary Dataframe...https://taxfoundation.org/taxedu/glossary/adjusted-gross-income-agi/
      if tax_filing == 'joint':
        filer_name = 'Joint'
      else:
        filer_name = filers[0]
      tax_df = pd.DataFrame({'filer':filer_name,
                'gross_income':gross_taxable_income,
                'MAGI':modified_adjusted_gross_income,
                'AGI':adjusted_gross_income,
                'fed_deduction':fed_deduction['amt'],
                'fed_deduction_name':fed_deduction['name'],
                'fed_income_tax':fed_income_tax,
                'state_deduction':state_deduction['amt'],
                'state_deduction_name':state_deduction['name'],
                'state_income_tax':state_income_tax,
                'payroll_tax':payroll_tax,
                'total_tax':total_tax})
      # print(tax_df.head(5))
      tax_df_dict[tax_filing] |= {filer_name:tax_df}
  return(tax_df_dict)

# After all income has been taxed, and all expenses have been paid, the leftover
# money will be put into savings. At some point, the 'bucket filling' allocation of
# savings to different accounts will be possible. In many ways, this function is the workhorse
# of the Income/Expense Cash Flow process.

# Drawdown Order
# Split Expenses
# Marriage

def balance_and_tax(plan):
    """
    Main balance and tax calculation process.
    
    Calculates taxes, balances income vs expenses, handles savings/drawdowns,
    and generates analytical time series.
    
    Args:
        plan: The plan object to balance and tax
        
    Returns:
        Updated plan object with taxes and balanced cash flow
    """
    def _sum_series(series_list, cal_year):
        if len(series_list) == 0:
            return pd.Series(0, index=cal_year)
        return sum(series_list)
    
    plan = plan.standardize_all_series()
    #plan = plan.project_all()
    
    # print(plan.aggregate('Expense','Joint'))
    # print(plan.aggregate('Income','Joint'))
    adults = [person.id for person in plan.people if person.dependent == False]
    
    # Remove any tax objects, as they will be fully recomputed
    #tax_inds = [plan.expenses.index(exp) for exp in plan.expenses if ((exp.category == 'Tax') & (exp.subcategory in ['Income','Payroll']))]
    #print([(obj.name,obj.person) for obj in plan.expenses])
    #print(tax_inds)
    #for ind in tax_inds:
    #    plan.expenses.pop(ind)
    plan.expenses = [exp for exp in plan.expenses if ((exp.category != 'Tax') | (exp.subcategory not in ['Income','Payroll']))]

    # Flag missing expense components (quiet unless issues detected)
    missing_components = []
    for exp in plan.expenses:
        if exp.person == 'Joint' and hasattr(exp, 'components'):
            for person_id, comp in exp.components.items():
                if comp is None:
                    missing_components.append((exp.name, exp.subcategory, person_id))
    if len(missing_components) > 0:
        print(f"[balance_and_tax] missing expense components: {missing_components}")

    # This is about determining the best tax filing scenario
    total_tax_list = []
    full_tax_list = []

    for filing_status in plan.tax_df_dict.keys():
    # First, append all dfs in tax_df_dict[filing_status]
        for filer in plan.tax_df_dict[filing_status].keys():
            full_tax_list.append(plan.tax_df_dict[filing_status][filer].assign(filing_status = filing_status))
    #
        if len(plan.tax_df_dict[filing_status].keys())==2:
            temp = pd.concat(plan.tax_df_dict[filing_status].values()).reset_index(drop=False).loc[:,['index','total_tax']].groupby('index').sum()
        else:
            temp = pd.concat(plan.tax_df_dict['joint'].values()).loc[:,['total_tax']]
        temp.loc[:,'filing_status'] = filing_status
        total_tax_list.append(temp)
  #
    full_tax_df  = pd.concat(full_tax_list)
    #
    total_tax_df = pd.concat(total_tax_list).reset_index(drop=False)
    single_df = total_tax_df.loc[total_tax_df['index'].isin(list(plan.married.index[~plan.married])) & total_tax_df['filing_status'].isin(['single']),:]
    married_df = total_tax_df.loc[total_tax_df['index'].isin(list(plan.married.index[plan.married])) & total_tax_df['filing_status'].isin(['joint','separate']),:]
    total_tax_df = pd.concat([single_df,married_df]).reset_index(drop=True)        
    total_tax_sorted = total_tax_df.groupby("index").agg({'total_tax':['idxmin','min']}).droplevel(0,axis=1) #.merge(all_state_deductions[['index','name']],left_on='idxmax',right_index=True).drop(['idxmax','index'],axis=1).rename(columns={'max':'amt'})
    best_filing_status = total_tax_df.reset_index(drop=False).loc[total_tax_sorted['idxmin'],['index','filing_status']].set_index('index')
    
    best_tax_df = []
    for yr in best_filing_status.index:
        best_tax_df.append(full_tax_df.loc[(full_tax_df.index==yr)&(full_tax_df['filing_status']==best_filing_status.loc[yr,'filing_status'])])
      
    plan.tax_df = pd.concat(best_tax_df)
  
    # Create Tax Expense Objects

    for filer in plan.tax_df.filer.unique():
        for col, name in {'state_income_tax':['Income','State'],'fed_income_tax':['Income','Federal'],'payroll_tax':['Payroll','Payroll']}.items():
            tax_series = plan.tax_df.loc[plan.tax_df['filer']==filer, col]
            tax_series = tax_series.replace([np.inf, -np.inf], np.nan).fillna(0).astype(int)
            exp = objs.financial_objects.ExpenseObj(filer,'Tax',name[0],name[1],'',
                              plan.cal_year,
                              tax_series,
                              True,False)
            plan.expenses.append(exp)
            plan = exp.project(plan)

  
    # Loop of people, years to contribute to or draw down a savings account
    # print('Getting into Person Loop on Balance')
    for person in adults:
        # First, clear all contributions from drawdown items
        for acct in plan.drawdown_order[person]:
            obj = plan.get_object_from_id(acct)
            obj.contribution = pd.Series(0,index=obj.cal_year)
            plan = obj.project(plan)
        
        # Use only non-savings expenses when determining surplus available for savings
        # to prevent double-counting contributions
        non_savings_categories = ['Necessary','Discretionary','Tax']
        expenses_series_list = []
        for exp in plan.expenses:
            if exp.category in non_savings_categories and hasattr(exp, 'components') and person in exp.components:
                expenses_series_list.append(exp.components[person])
        total_expenses = sum(expenses_series_list) if len(expenses_series_list) > 0 else pd.Series(0, index=plan.cal_year)
        # print('Person: ',person)
        # print('Total Expenses: ',total_expenses[2024])
        #print(total_expenses)
        total_income = sum([inc.value for inc in plan.income if inc.category == 'Earned' and inc.person == person])
        # print('Total Income: ',total_income[2024])
        difference  = total_income - total_expenses
        # print('Total Difference: ',difference[2024])
        
        # Loop over years, reproject savings accts each time (computationally cheap)
        # If 
        for yr in plan.cal_year:
            amt = difference[yr]
            if amt >= 0.0:
                # Guard: if no savings accounts configured for this person, skip deposit
                if person not in plan.drawdown_order or len(plan.drawdown_order[person]) == 0:
                    pass
                else:
                    first_id = plan.drawdown_order[person][0]
                    first_obj = plan.get_object_from_id(first_id)
                    if first_obj is None or first_obj.obj_type == 'Liability':
                        # No eligible savings account found
                        pass
                    else:
                        first_obj.contribution[yr] += int(amt)
                        plan = first_obj.project(plan)
            else:
                plan = plan.drawdown(amt,yr,person)
      #plan = plan.project_all()

    #Lastly, compute analytical timeseries
    df_list = []
    for person in adults+['Joint']:
        df = utils.plotting.compute_analytical_timeseries(plan, person)
        df['person'] = person
        df_list.append(df)
    plan.analytical_timeseries = pd.concat(df_list)
    
    return(plan)
