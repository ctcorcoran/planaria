# Planaria Class Hierarchy and Methods

## Overview

Planaria uses an object-oriented design with a clear class hierarchy for modeling financial objects and plans. This document provides a comprehensive reference for all classes, their attributes, and methods.

## Class Hierarchy

```
FinObj (Base Class)
├── IncExpObj (Income/Expense Base)
│   ├── IncomeObj
│   └── ExpenseObj
├── AssetObj
└── LiabObj

Person (Standalone)
Plan (Standalone)
NpEncoder (Utility)
```

## Core Classes

### 1. FinObj (Base Financial Object)

**File**: `objs/financial_objects.py`  
**Purpose**: Base class for all financial objects (Income, Expenses, Assets, Liabilities)

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `plan_id` | int | Plan identifier (always 1) |
| `person` | str | Owner of the object (Person ID or 'Joint') |
| `obj_type` | str | Object type ('Income', 'Expense', 'Asset', 'Liability') |
| `category` | str | Broad classification |
| `subcategory` | str | Specific type |
| `name` | str | Human-readable name |
| `editable` | bool | Whether object can be modified in UI |
| `cal_year` | pd.Series | Calendar years for the object |
| `start_year` | int | First year of activity |
| `end_year` | int | Last year of activity |
| `value` | pd.Series | Values over time |
| `dependent_objs` | bool | Whether object has dependent children |
| `paired_attr` | dict | Relationship data for networks |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `obj_type, person, cat, subcat, name, cal_year, value, editable, attributes={}` | None | Initialize financial object |
| `to_dataframe` | None | pd.DataFrame | Convert object to DataFrame |
| `to_serializable` | None | dict | Convert to JSON-serializable format |
| `standardize_timeseries` | `cal_year` | self | Standardize time series to plan calendar |
| `project` | `plan, init_id=None` | plan | Main workhorse method for dependency resolution |

### 2. IncExpObj (Income/Expense Base)

**File**: `objs/financial_objects.py`  
**Purpose**: Base class for Income and Expense objects

#### Additional Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `fixed` | bool | Whether value is fixed or inflates over time |
| `value_input` | pd.Series | Uninflated input values |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `obj_type, person, cat, subcat, name, cal_year, value, fixed, editable, attributes` | None | Initialize income/expense object |
| `inflate` | None | self | Apply inflation to values over time |
| `deflate` | None | self | Remove inflation (DEPRECATED) |

### 3. IncomeObj

**File**: `objs/financial_objects.py`  
**Purpose**: Represents income sources (salary, pension, etc.)

#### Additional Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `taxable` | bool | Whether income is subject to taxation |
| `pension` | pd.Series | Calculated pension income (if configured) |
| `pension_params` | dict | Pension calculation parameters |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `person, cat, subcat, name, cal_year, value, fixed, taxable, editable, attributes={}` | None | Initialize income object |
| `update` | None | self | Update income values and calculate pension |
| `make_pension_asset` | `plan, contribution_rate=0.06, asset_multiplier=12.0` | plan | Create pension-related objects |
| `remove_pension` | `plan` | plan | Remove pension configuration |
| `get_pension_contribution_rate` | `plan` | float | Get current pension contribution rate |

### 4. ExpenseObj

**File**: `objs/financial_objects.py`  
**Purpose**: Represents expenses (necessary, discretionary, savings)

#### Additional Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `tax_keyword` | str | Tax classification keyword |
| `components` | dict | Each person's share of expense value |
| `share_props` | pd.Series | Proportional sharing for joint expenses |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `person, cat, subcat, name, tax_keyword, cal_year, value, fixed, editable, attributes={}` | None | Initialize expense object |
| `set_props` | `plan` | self | Set proportional sharing properties |
| `adjust_share` | None | self | Adjust expense sharing proportions |
| `update` | None | self | Update expense values and components |

### 5. AssetObj

**File**: `objs/financial_objects.py`  
**Purpose**: Represents assets (retirement accounts, savings, real estate, etc.)

#### Additional Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `growth_rate` | pd.Series | Annual growth rate over time |
| `contribution` | pd.Series | Annual contributions |
| `secondary_contribution` | pd.Series | Secondary contributions (e.g., employer match) |
| `transaction` | pd.Series | Additional transactions |
| `tax_keyword` | str | Tax classification keyword |
| `interest` | bool | Whether interest is taxable |
| `sold` | int | Sale state (0=never, 1=sold, -1=reversed) |
| `gains` | pd.Series | Calculated gains over time |
| `props` | pd.Series | Proportional relationships |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `person, cat, subcat, name, tax_keyword, cal_year, value, growth_rate, contribution, interest, editable, attributes={}` | None | Initialize asset object |
| `update` | None | self | Update asset values and calculate gains |
| `make_expense_obj` | `plan, keyword, props=1.0` | plan | Create related expense objects |
| `make_401k_objs` | `plan, inc_obj_id, props, match_prop_max` | plan | Create 401k and related objects |
| `sell` | `plan, year, prune=False` | plan | Sell asset and handle proceeds |
| `reverse_sale` | `plan, year, prune=False` | plan | Reverse a previous sale |
| `deposit` | `amt, year` | self | Add money to asset |
| `withdrawal` | `amt, year` | self | Remove money from asset |

### 6. LiabObj

**File**: `objs/financial_objects.py`  
**Purpose**: Represents liabilities (mortgages, loans, credit cards)

#### Additional Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `interest_rate` | pd.Series | Annual interest rate over time |
| `existing` | bool | Whether liability already exists |
| `tax_keyword` | str | Tax classification keyword |
| `principal` | float | Original principal amount |
| `present_value` | float | Current present value |
| `payment` | float | Monthly payment amount |
| `term` | int | Term in months |
| `term_in_years` | bool | Whether term is specified in years |
| `extra_payment` | list | Extra payments by month |
| `payment_annual` | pd.Series | Annual payment amounts |
| `interest_payment_annual` | pd.Series | Annual interest payments |
| `extra_payment_annual` | pd.Series | Annual extra payments |
| `total_payment_annual` | pd.Series | Total annual payments |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `person, cat, subcat, name, tax_keyword, cal_year, interest_rate, value, existing, editable, attributes` | None | Initialize liability object |
| `amortize` | None | self | Calculate amortization schedule |
| `annualize_amort` | None | self | Convert monthly to annual payments |
| `update` | None | self | Update liability values and payments |
| `make_expense_obj` | `plan` | plan | Create related expense objects |

### 7. Person

**File**: `objs/plan.py`  
**Purpose**: Represents people in the financial plan

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Person's name |
| `birth_year` | int | Year of birth |
| `cal_year` | pd.Series | Calendar years |
| `current_age` | int | Current age |
| `age` | pd.Series | Age over time |
| `dependent` | bool | Whether person is a dependent |
| `child_cost_df` | pd.DataFrame | Child cost data (for dependents) |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `name, birth_year, cal_year, dependent, pet=False` | None | Initialize person |
| `standardize_timeseries` | `cal_year` | self | Standardize time series |
| `to_serializable` | None | dict | Convert to JSON-serializable format |

### 8. Plan

**File**: `objs/plan.py`  
**Purpose**: Main container for the entire financial plan

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Plan name |
| `start_year` | int | Plan start year |
| `n_years` | int | Number of years in plan |
| `cal_year` | pd.Series | Calendar years |
| `infl_rate` | float | Inflation rate |
| `col_rate` | float | Cost of living rate |
| `people` | list | List of Person objects |
| `events` | list | List of future events |
| `income` | list | List of IncomeObj objects |
| `expenses` | list | List of ExpenseObj objects |
| `assets` | list | List of AssetObj objects |
| `liabilities` | list | List of LiabObj objects |
| `pairs` | dict | Object relationship networks |
| `drawdown_order` | dict | Asset drawdown order by person |
| `married` | pd.Series | Marriage status over time |
| `marriage_year` | int | Year of marriage |
| `combined_expenses` | pd.Series | Combined expense status |
| `combine_year` | int | Year expenses were combined |
| `expense_share` | str | Expense sharing method |
| `dependents` | pd.Series | Number of dependents over time |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `name, start_year, n_years, infl_rate, col_rate` | None | Initialize plan |
| `reorder_object_ids` | None | self | Reorder object IDs for consistency |
| `to_json_string` | None | str | Convert plan to JSON string |
| `get_id_from_name` | `obj_type, name, person=None` | str | Get object ID from name |
| `get_object_from_id` | `ID` | object | Get object by ID |
| `get_object_from_name` | `obj_type, name, person=None` | object | Get object by name |
| `remove_object_by_id` | `ID` | self | Remove object and dependencies |
| `project_all` | None | self | Project all objects in plan |
| `get_tax_keyword_objects` | `tax_keyword` | list | Get objects by tax keyword |
| `standardize_all_series` | None | self | Standardize all time series |
| `aggregate` | `obj_type, person='Joint'` | pd.Series | Aggregate objects by type |
| `get_married` | `year` | self | Set marriage status |
| `generate_expense_share` | None | self | Generate expense sharing proportions |
| `drawdown` | `amt, year, person, keyword=None` | self | Withdraw from assets |
| `combine_expense` | `obj_name, comb_year` | self | Combine single expense |
| `combine_expenses` | `obj_name_list, comb_year` | self | Combine multiple expenses |
| `uncombine_expense` | `obj_name` | self | Uncombine single expense |
| `uncombine_expenses` | `obj_name_list` | self | Uncombine multiple expenses |
| `calculate_income_and_payroll_tax` | None | dict | Calculate tax information |
| `balance_and_tax` | None | self | Balance plan and calculate taxes |
| `pie_chart` | `obj_type, year, plot_type='pie', include_events=False, cats_to_ignore=[]` | dict | Generate pie chart data |
| `expense_plots` | `person, level, after_tax=False` | dict | Generate expense plots |
| `asset_plots` | `person, level, net_worth_formula=2` | dict | Generate asset plots |
| `cashflow_sankey` | `person, year, comb_all_exp=False, normalize=False` | dict | Generate cash flow diagram |
| `ratio_plot` | `person, names` | dict | Generate ratio plots |

### 9. NpEncoder

**File**: `objs/plan.py`  
**Purpose**: Custom JSON encoder for NumPy data types

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `default` | `obj` | serializable | Convert NumPy types to JSON-serializable |

## Key Design Patterns

### 1. Object ID Generation
All objects use a consistent ID pattern: `{obj_type}_{counter}`
- `Income_1`, `Asset_3`, `Liability_2`, etc.
- Counters are class-level static variables

### 2. Time Series Standardization
All objects use `standardize_timeseries()` to ensure consistent calendar years across the plan.

### 3. Dependency Networks
Objects use `paired_attr` dictionaries to define relationships in three networks:
- `series`: Value-based relationships
- `time`: Timing synchronization
- `share`: Proportional relationships

### 4. Projection Pattern
The `project()` method is the main workhorse that:
- Updates object values
- Resolves dependencies
- Prevents infinite loops
- Propagates changes through networks

### 5. Serialization
All objects implement `to_serializable()` for JSON export/import functionality.

## Usage Examples

### Creating a Simple Income Object
```python
income = IncomeObj(
    person="Person_1",
    cat="Earned", 
    subcat="Salary",
    name="Primary Salary",
    cal_year=plan.cal_year,
    value=75000,
    fixed=False,
    taxable=True,
    editable=True
)
```

### Creating an Asset with 401k Relationship
```python
asset = AssetObj(
    person="Person_1",
    cat="Investment",
    subcat="Retirement", 
    name="401k",
    tax_keyword="401k",
    cal_year=plan.cal_year,
    value=0,
    growth_rate=0.07,
    contribution=0,
    interest=False,
    editable=True
)

# Create 401k relationship with income
asset.make_401k_objs(plan, income.id, 0.15, 0.06)
```

### Projecting All Objects
```python
# Update all objects and resolve dependencies
plan = plan.project_all()

# Balance and calculate taxes
plan = plan.balance_and_tax()
```

This class hierarchy provides a robust foundation for modeling complex financial scenarios with automatic dependency resolution and relationship management.
