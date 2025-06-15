"""
Google Trends API implementations package.
Contains implementations for various Google Trends APIs:
- SerpAPI (paid)
- SerpWow (paid)
- SearchAPI (paid)
- TrendsPy (free)
- SerpApiPy (paid)
- ApplescriptSafari (free)
- DummyApi (free)
- WinUiautoEdge (free, not implemented)
"""

from .api_utils import change_tor_identity, standard_dict_to_df, load_api_config
from ..date_ranges import DateRange
from .serpapi import SerpApi
from .serpwow import SerpWow
from .searchapi import SearchApi
from .trendspy import TrendsPy
from .serpapi_python import SerpApiPy as SerpApiPy
from .applescript_safari import ApplescriptSafari
from .dummy_api import DummyApi
from .win_uiauto_edge import WinUiautoEdge

# Load API metadata from configuration
available_apis = load_api_config()

def get_free_apis():
    """Get dictionary of available free APIs with their metadata"""
    return {name: info for name, info in available_apis.items() 
            if info['type'] == 'free'}

def get_paid_apis():
    """Get dictionary of available paid APIs with their metadata"""
    return {name: info for name, info in available_apis.items() 
            if info['type'] == 'paid'}

def get_api_info(name: str):
    """Get metadata for a specific API"""
    return available_apis.get(name)

# Make all API classes and utility functions available
__all__ = ['SerpApi', 'SerpWow', 'SearchApi', 'TrendsPy', 'SerpApiPy', 'ApplescriptSafari', 'DummyApi', 'WinUiautoEdge',
           'available_apis', 'get_free_apis', 'get_paid_apis', 'get_api_info',
           'DateRange', 'change_tor_identity', 'standard_dict_to_df']

# Note: As far as I can tell, SerpApi and SearchApi always return the same data.
# Note that trendspy is very easily rate-limited, enough so that it might not even be usable.