# Core API Reference

## Trends Class

The main entry point for interacting with Google Trends data.

### Initialization
```python
from gtrend_api_tools import Trends

trends = Trends(
    api="applescript_safari",  # API implementation to use
    verbose=True,              # Enable verbose output
    proxy=None,               # Optional proxy settings
    change_identity=False     # Whether to change identity between requests
)
```

### Methods

#### search
```python
results = trends.search(
    search_term="term1,term2",  # Search terms (comma-separated)
    start_date="2024-01-01",    # Start date (YYYY-MM-DD)
    end_date="2024-03-01",      # End date (YYYY-MM-DD)
    granularity="day"           # Data granularity (day, week, month)
)
```

Returns a dictionary containing the search results.

#### get_available_apis
```python
apis = trends.get_available_apis()
```

Returns a list of available API implementations.

### Configuration

The Trends class can be configured through a YAML file. See the configuration section for details.

## Utility Functions

### load_config
```python
from gtrend_api_tools import load_config

config = load_config()
```

Loads configuration from the default config file.

### get_index_granularity
```python
from gtrend_api_tools import get_index_granularity

granularity = get_index_granularity(start_date, end_date)
```

Determines the appropriate granularity for a given date range.

### calculate_search_granularity
```python
from gtrend_api_tools import calculate_search_granularity

granularity = calculate_search_granularity(start_date, end_date)
```

Calculates the optimal search granularity based on date range.

### save_to_csv
```python
from gtrend_api_tools import save_to_csv

save_to_csv(results, filename)
```

Saves search results to a CSV file. 