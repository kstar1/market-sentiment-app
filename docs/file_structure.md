# 📁 Project File Overview

## 🔹 src/ui/filters_sidebar.py
Renders grouped sidebar widgets for filtering options data.

### Functions:
- `render_sidebar_filters(option_type, df)`: Adds strike, volume, IV, and OI sliders. Returns selected ranges.

## 🔹 streamlit_app.py
Main controller that ties together UI, data loading, and interactive filtering.

- Adds Reset Filters button.
- Creates CALL/PUT tabs with summary metrics.
- Filters data using inputs from `filters_sidebar.py`.


## 🔹 test/test_option_loader.py
Test harness to independently test data loading functions.
