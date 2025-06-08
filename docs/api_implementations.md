# API Implementations

The package supports multiple API implementations for accessing Google Trends data. Each implementation has its own advantages and limitations.

## Available APIs

### AppleScript Safari (Free)
- Uses AppleScript to automate Safari browser
- No API key required
- Limited to macOS systems
- Slower but reliable

### SerpAPI (Paid)
- Uses SerpAPI service
- Requires API key
- Fast and reliable
- Rate limits apply

### TrendsPy (Free)
- Uses pytrends library
- No API key required
- Good for basic use cases
- May have rate limits

### Windows UIAutomation Edge (Free)
- Uses Windows UI Automation
- Limited to Windows systems
- No API key required
- Browser automation based

## API Selection

When initializing the Trends class, you can specify which API to use:

```python
from gtrend_api_tools import Trends

# Use AppleScript Safari
trends = Trends(api="applescript_safari")

# Use SerpAPI
trends = Trends(api="serpapi")

# Use TrendsPy
trends = Trends(api="trendspy")
```

## API Information

You can get information about available APIs:

```python
from gtrend_api_tools import available_apis, get_free_apis, get_paid_apis

# Get all available APIs
all_apis = available_apis()

# Get only free APIs
free_apis = get_free_apis()

# Get only paid APIs
paid_apis = get_paid_apis()
```

## API Configuration

Each API implementation may require specific configuration. See the configuration section for details on how to set up each API. 