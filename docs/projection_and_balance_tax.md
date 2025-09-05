# Planaria Projection and Balance & Tax Processes

## Overview

Planaria uses a sophisticated multi-step process to project financial plans forward through time, handling inflation, interest, compounding, and complex financial relationships. This document explains how the model processes time progression and maintains financial balance.

## The Projection Process

### 1. High-Level Flow

The projection process follows this sequence:

1. **Event Processing** - Apply future events (marriage, expenses, etc.)
2. **Object Projection** - Update all financial objects through time
3. **Dependency Resolution** - Resolve object relationships and networks
4. **Tax Calculation** - Compute income and payroll taxes
5. **Balance & Cash Flow** - Balance income vs. expenses, handle savings/drawdowns
6. **Analytical Series** - Generate analytical time series for reporting

### 2. Core Projection Method: `project()`

Every financial object implements the `project()` method, which is the workhorse of the projection system:

```python
def project(self, plan, init_id=None):
    # 1. Standardize time series to plan calendar
    self = self.standardize_timeseries(plan.cal_year)
    
    # 2. Handle child components (for complex objects)
    if "child_components" in self.__dict__.keys():
        self.value_input = sum([x for x in self.child_components.values()])
    
    # 3. Process dependency networks (series, time, share)
    # ... network processing logic ...
    
    # 4. Update object-specific values
    self = self.update().standardize_timeseries(plan.cal_year)
    
    # 5. Recursively project dependent objects
    if self.dependent_objs == True:
        for child_id in [pair[1] for lst in plan.pairs.values() for pair in lst if pair[0]==self.id]:
            child_obj = plan.get_object_from_id(child_id)
            plan = child_obj.project(plan, init_id)
    
    return plan
```

## Time Series Standardization

### Purpose
All objects must have consistent time series aligned with the plan's calendar years.

### Process
```python
def standardize_timeseries(self, cal_year):
    # Apply plan.cal_year to object's time series
    # Add zeros for missing years (front/back padding)
    # Ensure consistent indexing across all objects
```

### Key Features
- **Front Padding**: Missing early years filled with specified values
- **Back Padding**: Missing future years filled with specified values  
- **Gap Filling**: Missing middle years filled with zeros
- **Index Alignment**: All series use same year-based index

## Inflation Processing

### 1. Income and Expense Inflation

Income and expense objects handle inflation through the `inflate()` method:

```python
def inflate(self):
    if self.fixed == True:
        # Fixed amounts don't inflate
        pass
    else:
        # Apply cumulative inflation
        self.value_input = expand_contract(self.value_input, self.cal_year)
        self.infl_rate = expand_contract(self.infl_rate, self.cal_year)
        
        # Calculate cumulative inflation factor
        cumulative_infl = [
            1 if yr == min(self.cal_year) 
            else pd.Series(1+self.infl_rate.loc[self.cal_year[0]:yr]).product() 
            for yr in self.cal_year
        ]
        
        # Apply inflation to values
        self.value = (self.value_input * pd.Series(cumulative_infl, index=self.cal_year)).astype(int)
```

### 2. Inflation Rate Application

- **Cumulative Calculation**: `(1 + r1) × (1 + r2) × ... × (1 + rn)`
- **Time-Based**: Inflation rates can vary by year
- **Preservation**: Original `value_input` is preserved for deflation
- **Fixed vs. Variable**: Objects can be marked as fixed (no inflation)

### 3. Tax Bracket Inflation

Tax brackets and thresholds are automatically inflated:

```python
# In calculate_income_and_payroll_tax()
tax_vals[level][name] = {
    filing_status: utils.utilities.inflate_amount(
        tax_vals[level][name][filing_status], 
        plan.infl_rate
    ) 
    for filing_status in tax_vals[level][name]
}
```

## Asset Growth and Compounding

### 1. Asset Value Calculation

Assets grow through a combination of:
- **Existing Value**: Previous year's value
- **Growth Rate**: Annual return percentage
- **Contributions**: New money added
- **Secondary Contributions**: Employer matches, etc.
- **Transactions**: Manual deposits/withdrawals

```python
def update(self):
    # Standardize all time series
    for attr in ['growth_rate', 'value', 'contribution', 'secondary_contribution', 'transaction']:
        setattr(self, attr, expand_contract(getattr(self, attr), self.cal_year))
    
    # Calculate compound growth
    temp_val = []
    for yr in self.cal_year:
        if yr == self.start_year:
            temp_val.append(self.value[yr])
        else:
            # Compound growth formula
            temp_val.append(
                temp_val[-1] * (1 + self.growth_rate[yr]) + 
                self.contribution[yr] + 
                self.secondary_contribution[yr] + 
                self.transaction[yr]
            )
    
    self.value = pd.Series(temp_val, index=self.cal_year).astype(int)
    self.gains = self.value.diff(1).shift(-1)  # Calculate gains
```

### 2. Compound Growth Formula

For each year: `Value_t = Value_{t-1} × (1 + GrowthRate_t) + Contributions_t + Transactions_t`

### 3. Growth Rate Flexibility
- **Variable Rates**: Growth rates can change over time
- **Asset-Specific**: Different assets can have different growth rates
- **Market Conditions**: Rates can reflect changing market conditions

## Liability Amortization

### 1. Amortization Process

Liabilities use standard amortization calculations:

```python
def amortize(self):
    # Calculate payment amount
    self.payment = utils.utilities.pmt(self.present_value, self.interest_rate, self.term)
    
    # Generate amortization schedule
    for i in range(self.term):
        pv = value[-1]  # Present value
        interest_payment = utils.utilities.ipmt(pv, self.interest_rate)
        principal_payment = utils.utilities.ppmt(pv, self.interest_rate, self.payment)
        
        # Update remaining balance
        value.append(pv - principal_payment - extra_payment[i])
```

### 2. Payment Components
- **Principal Payment**: Reduces loan balance
- **Interest Payment**: Interest on remaining balance
- **Extra Payment**: Additional principal payments
- **PMI**: Private Mortgage Insurance (for mortgages)

### 3. Annual Conversion
Monthly amortization schedules are converted to annual totals for projection purposes.

## Balance and Tax Process

### 1. Overview

The `balance_and_tax()` process is the main workhorse that:
1. Calculates taxes for all filing scenarios
2. Balances income vs. expenses
3. Handles savings and drawdowns
4. Generates analytical time series

### 2. Tax Calculation Process

```python
def calculate_income_and_payroll_tax(plan):
    # 1. Determine filing statuses (single, joint, separate)
    # 2. Inflate tax brackets and thresholds
    # 3. Calculate taxes for each filing scenario
    # 4. Determine optimal filing status
    # 5. Create tax expense objects
```

**Key Features**:
- **Multiple Filing Statuses**: Single, Joint, Separate
- **Optimization**: Chooses lowest tax scenario
- **Inflation Adjustment**: Tax brackets inflate with plan inflation
- **Comprehensive Coverage**: Federal, state, payroll taxes

### 3. Cash Flow Balancing

```python
def balance_and_tax(plan):
    # 1. Calculate total income and expenses by person
    # 2. Determine surplus/deficit for each year
    # 3. Handle positive cash flow (savings)
    # 4. Handle negative cash flow (drawdowns)
    
    for person in adults:
        total_income = sum([inc.value for inc in plan.income if inc.person == person])
        total_expenses = sum([exp.components[person] for exp in plan.expenses])
        difference = total_income - total_expenses
        
        for yr in plan.cal_year:
            if difference[yr] >= 0:
                # Surplus: Add to savings
                first_savings_account = plan.drawdown_order[person][0]
                first_savings_account.contribution[yr] += difference[yr]
            else:
                # Deficit: Draw down from savings
                plan = plan.drawdown(difference[yr], yr, person)
```

### 4. Drawdown Process

When expenses exceed income, the system draws down from savings:

```python
def drawdown(self, amt, year, person, keyword=None):
    amt_remaining = amt  # Always negative
    
    while amt_remaining > 0:
        # Get next account in drawdown order
        acct_id = self.drawdown_order[person][counter]
        acct_val = self.get_object_from_id(acct_id).value[year]
        
        if amt_remaining >= acct_val:
            # Withdraw entire account
            getattr(self.get_object_from_id(acct_id), keyword)[year] = -acct_val
            amt_remaining -= acct_val
        else:
            # Partial withdrawal
            getattr(self.get_object_from_id(acct_id), keyword)[year] = amt_remaining
            amt_remaining = 0
        
        # Re-project the account
        self = self.get_object_from_id(acct_id).project(self)
```

**Drawdown Order**: Assets are drawn down in a user-defined order (e.g., checking → savings → 401k → IRA).

## Dependency Network Processing

### 1. Series Network (Value Relationships)

Objects with series relationships automatically update based on parent values:

```python
# Example: 401k contribution from salary
for parent in self.paired_attr['series'].keys():
    for pair in self.paired_attr['series'][parent]:
        parent_attr, child_attr, scaling_factor = pair
        parent_value = getattr(plan.get_object_from_id(parent), parent_attr)
        setattr(self, child_attr, parent_value * scaling_factor)
```

### 2. Time Network (Timing Synchronization)

Objects with time relationships synchronize their start/end years:

```python
# Example: Home and mortgage start/end together
for parent in self.paired_attr['time'].keys():
    for pair in self.paired_attr['time'][parent]:
        parent_attr, child_attr, offset = pair
        parent_value = getattr(plan.get_object_from_id(parent), parent_attr)
        setattr(self, child_attr, parent_value + offset)
```

### 3. Share Network (Proportional Relationships)

Joint objects share values proportionally:

```python
# Example: Joint expenses split by income
if self.obj_type == 'Expense' and self.person == 'Joint':
    self = self.set_props(plan)  # Set sharing proportions
    self = self.adjust_share()   # Apply proportional splits
```

## Event Processing

### 1. Marriage Events

```python
# Apply marriage events first
for ev in st.session_state['plan'].events:
    if ev[1] == 'Get Married':
        year = ev[0]
        # Set married status
        st.session_state['plan'] = st.session_state['plan'].get_married(year)
        # Apply wedding budget withdrawals
        budget = int(payload.get('budget', 0))
        sources = payload.get('sources', [])
        for asset_id, prop in sources:
            amt = int(round(budget * (float(prop) / total_prop)))
            asset = st.session_state['plan'].get_object_from_id(asset_id)
            asset = asset.withdrawal(amt, year)
```

### 2. Expense Combination Events

```python
# Apply expense combination events
for ev in st.session_state['plan'].events:
    if ev[1] == 'Combine Expenses':
        names = ev[2].get('names', [])
        year = ev[0]
        st.session_state['plan'] = st.session_state['plan'].combine_expenses(names, year)
```

## Analytical Time Series Generation

After all projections are complete, analytical time series are generated:

```python
# Generate analytical time series for reporting
df_list = []
for person in adults + ['Joint']:
    df = utils.plotting.compute_analytical_timeseries(plan, person)
    df['person'] = person
    df_list.append(df)
plan.analytical_timeseries = pd.concat(df_list)
```

## Key Design Principles

### 1. Dependency Resolution
- Objects project in dependency order
- Parent objects project before children
- Infinite loops prevented with `init_id` parameter

### 2. Time Consistency
- All objects use same calendar years
- Time series are standardized before projection
- Gaps are filled with appropriate values

### 3. Financial Accuracy
- Compound growth calculations are precise
- Amortization follows standard formulas
- Tax calculations use current tax code

### 4. Flexibility
- Growth rates can vary over time
- Multiple filing statuses supported
- Custom drawdown orders allowed

### 5. Performance
- Efficient time series operations
- Minimal redundant calculations
- Optimized dependency traversal

## Example: Complete Projection Cycle

```python
# 1. Create plan
plan = Plan("My Plan", 2024, 30, 0.03, 0.02)

# 2. Add objects with relationships
salary = IncomeObj("Person_1", "Earned", "Salary", "Primary Salary", 
                   plan.cal_year, 75000, False, True, True)
plan.income.append(salary)

401k = AssetObj("Person_1", "Investment", "Retirement", "401k", "401k",
                plan.cal_year, 0, 0.07, 0, False, True)
401k.make_401k_objs(plan, salary.id, 0.15, 0.06)  # 15% contribution, 6% match

# 3. Project all objects
plan = plan.project_all()

# 4. Balance and calculate taxes
plan = plan.balance_and_tax()

# 5. Access results
print(plan.analytical_timeseries)
```

This projection system provides a robust, accurate, and flexible framework for modeling complex financial scenarios over time, handling all the nuances of real-world financial planning including inflation, compounding, taxes, and cash flow management.
