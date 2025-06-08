"""
Google Trends API Tools
A collection of tools for accessing Google Trends data through various APIs.
"""

__version__ = "0.1.0_alpha"

from .gtrend import Trends
from .utils import (
    load_config,
    get_index_granularity,
    calculate_search_granularity,
    save_to_csv
)
from .APIs import (
    available_apis,
    get_free_apis,
    get_paid_apis,
    get_api_info
)

__all__ = [
    'Trends',
    'load_config',
    'get_index_granularity',
    'calculate_search_granularity',
    'save_to_csv',
    'available_apis',
    'get_free_apis',
    'get_paid_apis',
    'get_api_info'
]
