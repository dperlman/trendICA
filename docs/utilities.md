# Utilities

The package provides several utility functions to help with common tasks.

## Configuration

### load_config
```python
from gtrend_api_tools import load_config

config = load_config()
```

Loads configuration from the default config file. The configuration can include:
- API settings
- Proxy settings
- Verbose mode
- Other global settings

## Data Processing

### get_index_granularity
```python
from gtrend_api_tools import get_index_granularity

granularity = get_index_granularity(start_date, end_date)
```

Determines the appropriate granularity for a given date range. Returns one of:
- "day"
- "week"
- "month"

### calculate_search_granularity
```python
from gtrend_api_tools import calculate_search_granularity

granularity = calculate_search_granularity(start_date, end_date)
```

Calculates the optimal search granularity based on date range. This helps optimize API calls and data retrieval.

## Data Export

### save_to_csv
```python
from gtrend_api_tools import save_to_csv

save_to_csv(results, filename)
```

Saves search results to a CSV file. The results should be in the format returned by the search method.

## API Utilities

### available_apis
```python
from gtrend_api_tools import available_apis

apis = available_apis()
```

Returns a list of all available API implementations.

### get_free_apis
```python
from gtrend_api_tools import get_free_apis

free_apis = get_free_apis()
```

Returns a list of free API implementations.

### get_paid_apis
```python
from gtrend_api_tools import get_paid_apis

paid_apis = get_paid_apis()
```

Returns a list of paid API implementations.

### get_api_info
```python
from gtrend_api_tools import get_api_info

info = get_api_info(api_name)
```

Returns detailed information about a specific API implementation. 