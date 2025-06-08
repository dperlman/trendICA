# Google Trends API Tools

A Python package providing a unified interface for accessing Google Trends data through various APIs.

## Quick Links
- [Documentation](docs/README.md)
- [Examples](examples/)
- [License](LICENSE)

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

## Features
- Multiple API implementations (free and paid options)
- Unified interface for all APIs
- Configurable through YAML
- Support for various data granularities
- Built-in utilities for data processing and export

## Documentation
For detailed documentation, please visit the [docs](docs/README.md) directory.

## Examples
Check out the [examples](examples/) directory for Jupyter notebooks demonstrating various use cases.

## Contributing
Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## License
This project is licensed under the terms of the license included in the repository.
