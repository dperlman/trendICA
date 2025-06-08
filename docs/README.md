# Google Trends API Tools Documentation

## Overview
Google Trends API Tools is a Python package that provides a unified interface for accessing Google Trends data through various APIs. The package supports multiple API implementations, including free and paid options.

## Installation
```bash
pip install gtrend_api_tools
```

## Quick Start
```python
from gtrend_api_tools import Trends

# Initialize with default settings
trends = Trends()

# Perform a search
results = trends.search(
    search_term="coffee,tea",
    start_date="2024-01-01",
    end_date="2024-03-01",
    granularity="day"
)
```

## Available APIs
The package supports multiple API implementations:
- AppleScript Safari (Free)
- SerpAPI (Paid)
- TrendsPy (Free)
- And more...

## Configuration
Configuration can be managed through a YAML file. See `config.yaml` for available options.

## Examples
Check the `examples/` directory for Jupyter notebooks demonstrating various use cases.

## API Reference
Detailed API documentation is available in the following sections:
- [Core API](core_api.md)
- [API Implementations](api_implementations.md)
- [Utilities](utilities.md)

## Contributing
Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## License
This project is licensed under the terms of the license included in the repository. 