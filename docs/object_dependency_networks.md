# Planaria Object Dependency Networks

## Overview

Planaria uses a sophisticated three-level object dependency network system to model complex financial relationships between objects. This system allows objects to automatically update their values based on changes to related objects, creating a dynamic and interconnected financial model.

## Architecture

### Core Components

1. **Plan Object** (`objs/plan.py`)
   - Contains the master network structure: `self.pairs = {'series':[],'time':[],'share':[]}`
   - Each network is a list of `[parent_id, child_id]` pairs
   - Manages object relationships and dependency propagation

2. **Financial Objects** (`objs/financial_objects.py`)
   - Each object has: `self.paired_attr = {'series':{},'time':{},'share':{}}`
   - Stores the actual relationship data and parameters
   - Implements the `project()` method for dependency resolution

3. **Utility Functions** (`utils/utilities.py`)
   - `get_all_descendants()` - Finds all child objects recursively
   - `get_all_ancestors()` - Finds all parent objects recursively
   - `get_future_event_object_ids()` - Gets all objects related to future events

## The Three Networks

### 1. Series Network (`'series'`)

**Purpose**: Links objects where one object's value directly influences another object's value over time.

**Structure**: 
- Parent object's attribute → Child object's attribute with scaling factor
- Format: `[parent_id, child_id, [parent_attr, child_attr, scaling_factor]]`

**Real-World Examples**:

1. **401(k) Contribution from Salary**
   - Parent: Income object (salary)
   - Child: Asset object (401k)
   - Relationship: `['value', 'contribution', 0.15]` (15% of salary goes to 401k)
   - When salary changes, 401k contribution automatically updates

2. **Employer 401(k) Match**
   - Parent: Income object (salary) 
   - Child: Income object (employer match)
   - Relationship: `['value', 'value', 0.06]` (6% employer match)
   - Automatically calculated as percentage of salary

3. **401(k) Secondary Contribution from Employer Match**
   - Parent: Income object (employer match)
   - Child: Asset object (401k)
   - Relationship: `['value', 'secondary_contribution', 1.0]` (100% of match goes to 401k)
   - Employer match automatically flows to 401k

4. **Property Tax from Home Value**
   - Parent: Asset object (home)
   - Child: Expense object (property tax)
   - Relationship: `['value', 'value', 0.012]` (1.2% property tax rate)
   - Property tax automatically updates when home value changes

5. **Home Maintenance from Home Value**
   - Parent: Asset object (home)
   - Child: Expense object (maintenance)
   - Relationship: `['value', 'value', 0.01]` (1% maintenance rate)
   - Maintenance costs scale with home value

6. **Liability Asset Value Tracking**
   - Parent: Asset object (home/car)
   - Child: Liability object (mortgage/loan)
   - Relationship: `['value', 'asset_value', 1.0]` (100% of asset value tracked)
   - Used for equity calculations and loan-to-value ratios

7. **Pension Contribution from Salary**
   - Parent: Income object (salary)
   - Child: Expense object (pension contribution)
   - Relationship: `['value', 'value', 0.08]` (8% pension contribution)
   - Pension contributions scale with salary

8. **Pension Asset from Pension Income**
   - Parent: Income object (salary with pension)
   - Child: Asset object (pension equivalent)
   - Relationship: `['pension', 'value', 12.0]` (12x pension multiplier)
   - Creates synthetic asset representing pension value

9. **Liability Payment from Liability**
   - Parent: Liability object (mortgage/loan)
   - Child: Expense object (payment)
   - Relationship: `['payment_annual', 'value', 1.0]` (100% of payment)
   - Payment expenses automatically track liability payments

10. **Liability Interest Payment from Liability**
    - Parent: Liability object (mortgage/loan)
    - Child: Expense object (interest payment)
    - Relationship: `['interest_payment_annual', 'interest_payment', 1.0]` (100% of interest)
    - Interest expenses automatically track liability interest

11. **Extra Payment from Liability**
    - Parent: Liability object (mortgage/loan)
    - Child: Expense object (extra payment)
    - Relationship: `['extra_payment_annual', 'value', 1.0]` (100% of extra payment)
    - Extra payment expenses automatically track additional payments

12. **Asset Contribution from Asset**
    - Parent: Asset object (savings account)
    - Child: Expense object (contribution)
    - Relationship: `['contribution', 'value', 1.0]` (100% of contribution)
    - Contribution expenses automatically track asset contributions

13. **Combined Expenses from Individual Expenses**
    - Parent: Multiple Expense objects (individual expenses)
    - Child: Expense object (combined expenses)
    - Relationship: `['value_input', 'value_input', 1.0]` (100% of each expense)
    - Individual expenses are combined into joint household expenses

**Implementation**:
```python
# In FinObj.project() method
for parent in self.paired_attr['series'].keys():
    for pair in self.paired_attr['series'][parent]:
        parent_attr, child_attr, scaling_factor = pair
        parent_value = getattr(plan.get_object_from_id(parent), parent_attr)
        setattr(self, child_attr, parent_value * scaling_factor)
```

**Complete List of Series Network Types**:

| # | Parent Object | Child Object | Parent Attribute | Child Attribute | Purpose |
|---|---------------|--------------|------------------|-----------------|---------|
| 1 | Income (Salary) | Asset (401k) | `value` | `contribution` | 401k contributions from salary |
| 2 | Income (Salary) | Income (Employer Match) | `value` | `value` | Employer 401k match |
| 3 | Income (Employer Match) | Asset (401k) | `value` | `secondary_contribution` | Employer match to 401k |
| 4 | Asset (Home) | Expense (Property Tax) | `value` | `value` | Property tax from home value |
| 5 | Asset (Home) | Expense (Maintenance) | `value` | `value` | Home maintenance costs |
| 6 | Asset (Home/Car) | Liability (Mortgage/Loan) | `value` | `asset_value` | Asset value tracking for equity |
| 7 | Income (Salary) | Expense (Pension Contribution) | `value` | `value` | Pension contributions from salary |
| 8 | Income (Salary) | Asset (Pension Equivalent) | `pension` | `value` | Synthetic pension asset value |
| 9 | Liability (Mortgage/Loan) | Expense (Payment) | `payment_annual` | `value` | Liability payment expenses |
| 10 | Liability (Mortgage/Loan) | Expense (Interest Payment) | `interest_payment_annual` | `interest_payment` | Liability interest expenses |
| 11 | Liability (Mortgage/Loan) | Expense (Extra Payment) | `extra_payment_annual` | `value` | Extra payment expenses |
| 12 | Asset (Savings) | Expense (Contribution) | `contribution` | `value` | Asset contribution expenses |
| 13 | Multiple Expenses | Expense (Combined) | `value_input` | `value_input` | Combined household expenses |

**Special Cases**:

- **Employer Match with Multiple Props**: The employer match relationship (#2) can have multiple scaling factors to handle complex matching formulas (e.g., 100% match up to 3%, then 50% match up to 6%)
- **Asset Value Tracking**: Relationship #6 is used for equity calculations and loan-to-value ratios, not for direct value transfer
- **Pension Multiplier**: Relationship #8 uses a multiplier (typically 12x) to convert annual pension income to equivalent asset value
- **Combined Expenses**: Relationship #13 aggregates multiple individual expenses into joint household expenses after marriage

### 2. Time Network (`'time'`)

**Purpose**: Synchronizes timing between objects, ensuring related objects start/end at the same time.

**Structure**:
- Parent object's timing attribute → Child object's timing attribute with offset
- Format: `[parent_id, child_id, [parent_attr, child_attr, offset_years]]`

**Real-World Examples**:

1. **Home Purchase with Mortgage**
   - Parent: Asset object (home)
   - Child: Liability object (mortgage)
   - Relationship: `['start_year', 'start_year', 0]` (both start same year)
   - Relationship: `['end_year', 'end_year', 0]` (both end same year)
   - When home is sold, mortgage is automatically paid off

2. **Car Purchase with Auto Loan**
   - Parent: Asset object (car)
   - Child: Liability object (auto loan)
   - Relationship: `['start_year', 'start_year', 0]` (purchase timing)
   - Relationship: `['end_year', 'end_year', 0]` (loan payoff timing)

3. **Retirement Account with Required Minimum Distributions**
   - Parent: Asset object (401k)
   - Child: Income object (RMD)
   - Relationship: `['start_year', 'start_year', 15]` (RMD starts 15 years after 401k)
   - RMD automatically begins when 401k holder reaches required age

**Implementation**:
```python
# In FinObj.project() method
for parent in self.paired_attr['time'].keys():
    for pair in self.paired_attr['time'][parent]:
        parent_attr, child_attr, offset = pair
        parent_value = getattr(plan.get_object_from_id(parent), parent_attr)
        setattr(self, child_attr, parent_value + offset)
```

### 3. Share Network (`'share'`)

**Purpose**: Manages shared ownership and proportional relationships between objects.

**Structure**:
- Parent object's value → Child object's share properties
- Format: `[parent_id, child_id, [parent_attr, child_attr, None]]`

**Real-World Examples**:

1. **Joint Expenses After Marriage**
   - Parent: Income objects (both spouses' salaries)
   - Child: Expense object (joint expenses)
   - Relationship: `['value', 'share_props', None]` (proportional to income)
   - Joint expenses are split based on income ratios

2. **Shared Asset Ownership**
   - Parent: Asset object (joint home)
   - Child: Person objects (both spouses)
   - Relationship: `['value', 'share_props', None]` (50/50 ownership)
   - Asset value is split between owners

3. **Combined Household Expenses**
   - Parent: Multiple expense objects (individual expenses)
   - Child: Expense object (combined expenses)
   - Relationship: `['value', 'share_props', None]` (aggregated expenses)
   - Individual expenses are combined into household total

**Implementation**:
```python
# In FinObj.project() method
if self.obj_type == 'Expense' and self.person == 'Joint':
    if 'share_props' not in self.__dict__.keys():
        self = self.set_props(plan)
```

## Object Attributes and Methods

### Core Attributes

**Every Financial Object Has**:
- `id`: Unique identifier (e.g., "Income_1", "Asset_3")
- `obj_type`: Object type ("Income", "Expense", "Asset", "Liability")
- `person`: Owner ("Person_1", "Person_2", "Joint")
- `category`: Broad classification ("Earned", "Necessary", "Retirement", etc.)
- `subcategory`: Specific type ("Salary", "401k", "Mortgage", etc.)
- `name`: Human-readable name
- `cal_year`: Pandas Series of calendar years
- `value`: Pandas Series of values over time
- `start_year`: First year of activity
- `end_year`: Last year of activity
- `editable`: Whether object can be modified in UI
- `dependent_objs`: Whether object has dependent children
- `paired_attr`: Dictionary containing relationship data

### Key Methods

**`project(plan, init_id=None)`**:
- Main workhorse method that updates object values
- Processes all three networks (series, time, share)
- Recursively updates dependent objects
- Prevents infinite loops with `init_id` parameter

**`standardize_timeseries(cal_year)`**:
- Ensures all time series match the plan's calendar years
- Pads with zeros for missing years
- Standardizes indexing across all objects

**`update()`**:
- Object-specific update logic
- Handles inflation, growth rates, transactions
- Updates object-specific attributes

## Network Traversal

### Descendant Finding
```python
def get_all_descendants(plan, obj_id):
    """Find all descendant objects recursively"""
    descendants = {'series': [], 'time': [], 'share': []}
    # Implementation uses iterative traversal to handle complex hierarchies
```

### Ancestor Finding
```python
def get_all_ancestors(plan, obj_id):
    """Find all ancestor objects recursively"""
    ancestors = {'series': [], 'time': [], 'share': []}
    # Implementation uses iterative traversal to handle complex hierarchies
```

### Future Event Filtering
```python
def get_future_event_object_ids(plan):
    """Get all objects related to future events (including descendants)"""
    future_event_ids = set()
    for event in plan.events:
        event_id = event[2]  # Object ID from event
        future_event_ids.add(event_id)
        # Add all descendants
        descendants = get_all_descendants(plan, event_id)
        for network in ['series', 'time', 'share']:
            future_event_ids.update(descendants[network])
    return future_event_ids
```

## Usage Patterns

### Creating Relationships
1. **Add to plan.pairs**: `plan.pairs['series'].append([parent_id, child_id])`
2. **Set paired_attr**: `child_obj.paired_attr['series'][parent_id] = [[parent_attr, child_attr, scaling_factor]]`
3. **Set dependent_objs**: `parent_obj.dependent_objs = True`

### Updating Objects
1. **Call project()**: `obj.project(plan)`
2. **Automatic propagation**: All dependent objects update automatically
3. **Loop prevention**: Uses `init_id` to prevent infinite recursion

### Filtering Current State
- Use `get_future_event_object_ids()` to exclude future event objects
- Apply filtering in UI pages to show only current state objects
- Ensures future events don't appear in current financial state

## Benefits

1. **Automatic Updates**: Changes propagate through the network automatically
2. **Complex Relationships**: Models real-world financial interdependencies
3. **Time Synchronization**: Ensures related objects stay in sync
4. **Proportional Sharing**: Handles joint ownership and shared expenses
5. **Future Event Management**: Cleanly separates current vs. future state
6. **Extensibility**: Easy to add new relationship types

## Best Practices

1. **Always set dependent_objs**: Mark parent objects that have children
2. **Use consistent naming**: Follow the established ID and attribute patterns
3. **Handle edge cases**: Consider what happens when objects are deleted
4. **Test relationships**: Verify that changes propagate correctly
5. **Document complex relationships**: Comment non-obvious relationship logic
6. **Use utility functions**: Leverage the provided traversal functions

This network system is the backbone of Planaria's dynamic financial modeling, enabling complex scenarios to be modeled with simple, declarative relationships between objects.
