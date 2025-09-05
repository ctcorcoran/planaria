# Planaria

A comprehensive financial planning application built with Python and Streamlit. Planaria helps you model your financial future by projecting income, expenses, assets, and liabilities over time with sophisticated tax calculations and dependency networks.

## Quick Launch (Windows)

For Windows users, you can create a convenient batch file to launch Planaria:

1. **Create `run.bat`** in the project root directory with the following content:
   ```batch
   call C:\path\to\your\anaconda3\Scripts\activate.bat
   cd C:\path\to\your\planaria\directory
   streamlit run app.py
   ```

2. **Update the paths** in the batch file to match your system:
   - Replace `C:\path\to\your\anaconda3\Scripts\activate.bat` with your Anaconda activation script path
   - Replace `C:\path\to\your\planaria\directory` with your actual Planaria project directory

3. **Double-click `run.bat`** to launch the application

**Purpose:** The batch file automatically activates your Python environment and launches Streamlit, eliminating the need to manually run terminal commands each time.

## Features

- **Comprehensive Financial Modeling**: Track income, expenses, assets, and liabilities
- **Advanced Tax Calculations**: Federal and state tax projections with itemized deductions
- **Object Dependency Networks**: Automatic calculations between related financial objects
- **Future Event Planning**: Model life events like marriage, children, and major purchases
- **Interactive Web Interface**: User-friendly Streamlit-based UI
- **Time Series Projections**: Multi-year financial planning with inflation and growth
- **Retirement Planning**: 401k, pension, and retirement account modeling
- **Real Estate Planning**: Mortgage calculations and property value tracking

## Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/planaria.git
   cd planaria
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install individually:
   ```bash
   pip install streamlit pandas numpy plotly
   ```

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

4. **Open your browser** to `http://localhost:8501`

## Usage

### Creating Your First Plan

1. **Start a new plan** using the sidebar
2. **Add people** to your financial plan
3. **Configure income sources** (salary, retirement contributions)
4. **Set up expenses** (housing, food, transportation, etc.)
5. **Add assets** (401k, savings accounts, real estate)
6. **Include liabilities** (mortgages, loans, credit cards)
7. **Run projections** to see your financial future
8. **Save your plan** for future reference

### Key Concepts

- **Financial Objects**: Income, expenses, assets, and liabilities with time series data
- **Dependency Networks**: Automatic relationships between objects (e.g., 401k contributions from salary)
- **Future Events**: Life changes that affect your financial plan over time
- **Tax Optimization**: Automatic calculation of optimal filing status and deductions

## Documentation

- **[Object Dependency Networks](docs/object_dependency_networks.md)** - How financial objects relate to each other
- **[Class Hierarchy](docs/class_hierarchy_and_methods.md)** - Technical architecture overview
- **[Projection & Tax Process](docs/projection_and_balance_tax.md)** - How calculations work
- **[Style Guide](docs/style_guide.txt)** - Development guidelines

## Current Status

**Beta Version** - This application is currently in beta testing. Core functionality is stable, but some features may have limitations:

- Tax calculations optimized for California
- Basic error handling
- Desktop-optimized interface
- Local file storage only

## Contributing

We welcome contributions! Please see our [Style Guide](docs/style_guide.txt) for development guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Follow the coding style guidelines
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and planning purposes only. It should not be used as the sole basis for financial decisions. Always consult with qualified financial professionals for important financial planning decisions.

## Support

For questions, issues, or feature requests, please:
1. Check the documentation first
2. Search existing issues
3. Create a new issue with detailed information

---=