# Planaria Beta Testing Guide

Welcome to the Planaria financial planning application beta test! This guide will help you get started and provide feedback to improve the application.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+ installed on your system
- Basic familiarity with financial planning concepts
- Willingness to report bugs and provide feedback

### Installation & Setup
1. **Clone/Download** the Planaria repository
2. **Install Dependencies:**
   ```bash
   pip install streamlit pandas numpy plotly
   ```
3. **Run the Application:**
   ```bash
   streamlit run app.py
   ```
4. **Open your browser** to the URL shown in the terminal (usually `http://localhost:8501`)

## 📋 Beta Testing Focus Areas

### Core Workflows to Test
1. **Creating a New Plan**
   - Set up basic plan parameters (start year, duration, inflation rates)
   - Add people to your plan

2. **Income Management**
   - Add salary/employment income
   - Configure retirement contributions (401k, pension)
   - Test different income scenarios

3. **Expense Tracking**
   - Add necessary expenses (housing, food, transportation)
   - Add discretionary expenses
   - Test expense sharing between people

4. **Asset Management**
   - Add retirement accounts (401k, IRA)
   - Add savings accounts
   - Add real estate assets
   - Test asset growth projections

5. **Liability Management**
   - Add mortgages, loans, credit cards
   - Test payment calculations and amortization

6. **Future Events**
   - Add marriage events
   - Add child birth events
   - Test how events affect projections

7. **Analysis & Reports**
   - Review net worth projections
   - Check ratio analysis
   - Examine cash flow projections

## 🐛 Known Issues & Limitations

### Current Limitations
- **Tax Calculations:** Currently configured for California state taxes only
- **Data Persistence:** Plans are saved locally as JSON files
- **Mobile Experience:** UI is optimized for desktop/laptop use
- **Error Messages:** Some error handling is still basic

### Known Quirks
- **Update Button:** Always click "Update Plan" after making changes
- **Child Expenses:** Child cost data is based on 2015 USDA data
- **Pension Calculations:** Complex pension scenarios may need manual verification

## 📝 How to Provide Feedback

### Bug Reports
When reporting bugs, please include:
1. **What you were trying to do**
2. **What happened instead**
3. **Steps to reproduce the issue**
4. **Screenshots** (if applicable)
5. **Your system info** (OS, Python version, browser)

### Feature Requests
For new features or improvements:
1. **Describe the feature** you'd like to see
2. **Explain why** it would be valuable
3. **Suggest how** it might work
4. **Provide examples** if possible

### General Feedback
- **What works well?**
- **What's confusing or unclear?**
- **What's missing** for your use case?
- **Performance issues** (slow loading, crashes)

## 🎯 Testing Scenarios

### Scenario 1: Young Professional
- Single person, age 25
- $60k salary with 6% 401k contribution
- $2k monthly rent, $500 monthly expenses
- Goal: Save for house down payment

### Scenario 2: Married Couple
- Two people, ages 30 and 28
- Combined income $120k
- $3k monthly mortgage, $1.5k monthly expenses
- Planning for children in 3 years

### Scenario 3: Pre-Retirement
- Married couple, ages 55 and 53
- Combined income $150k
- $500k in retirement accounts
- Planning retirement at 65

## 🔧 Troubleshooting

### Common Issues

**App won't start:**
- Check Python version: `python --version`
- Verify dependencies: `pip list | grep streamlit`
- Try: `streamlit run app.py --server.port 8502`

**Plans won't save:**
- Check `saved_plans/` directory exists
- Verify write permissions
- Try saving with a different name

**Calculations seem wrong:**
- Click "Update Plan" button
- Check that all required fields are filled
- Verify tax settings match your state

**UI looks broken:**
- Refresh the browser page
- Clear browser cache
- Try a different browser

### Getting Help
- **Documentation:** Check the `docs/` folder for technical details
- **Code Issues:** Look at the terminal output for error messages
- **Data Issues:** Verify your input data is reasonable

## 📊 What We're Looking For

### Critical Issues
- **Data Loss:** Plans that can't be saved or loaded
- **Calculation Errors:** Obviously wrong financial projections
- **Crashes:** Application stops working unexpectedly
- **Security Issues:** Data exposure or unauthorized access

### Usability Issues
- **Confusing Interface:** Unclear buttons, labels, or workflows
- **Missing Features:** Essential functionality that's not available
- **Performance Problems:** Slow loading or unresponsive interface
- **Data Entry Issues:** Difficult or error-prone input methods

### Enhancement Opportunities
- **Workflow Improvements:** Better ways to accomplish common tasks
- **Additional Features:** New capabilities that would be valuable
- **Integration Ideas:** Connections to other tools or data sources
- **Reporting Enhancements:** Better charts, tables, or export options

## 🎉 Success Criteria

The beta test will be considered successful if:
- [ ] Core financial planning workflows work reliably
- [ ] Users can create and save plans without data loss
- [ ] Calculations produce reasonable results
- [ ] UI is intuitive for basic financial planning tasks
- [ ] Feedback identifies clear improvement priorities

## 📞 Contact & Support

**For Beta Testing Issues:**
- Create detailed bug reports with reproduction steps
- Include screenshots and system information
- Test on different scenarios to isolate issues

**For Questions:**
- Check the documentation first
- Try the troubleshooting steps above
- Provide specific examples of what you're trying to accomplish

---

## 🏁 Thank You!

Your participation in the Planaria beta test is invaluable. Your feedback will help shape the future of this financial planning tool and make it more useful for everyone.

**Remember:** This is beta software. Save your work frequently, and don't rely on it for critical financial decisions without verification.

Happy testing! 🚀
