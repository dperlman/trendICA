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
"""

from .api_utils import make_time_range, change_tor_identity, standard_dict_to_df
from .serpapi import SerpApi
from .serpwow import SerpWow
from .searchapi import SearchApi
from .trendspy import TrendsPy
from .serpapi_python import SerpApiPy as SerpApiPy
from .applescript_safari import ApplescriptSafari
from .dummy import DummyApi

# Define API metadata
available_apis = {
    'trendspy': {
        'class': TrendsPy,
        'type': 'free',
        'description': 'Uses trendspy library for Google Trends data'
    },
    'serpapi': {
        'class': SerpApi,
        'type': 'paid',
        'description': 'Uses SerpAPI service with direct HTTP requests'
    },
    'serpwow': {
        'class': SerpWow,
        'type': 'paid',
        'description': 'Uses SerpWow service'
    },
    'searchapi': {
        'class': SearchApi,
        'type': 'paid',
        'description': 'Uses SearchAPI service'
    },
    'serpapi_python': {
        'class': SerpApiPy,
        'type': 'paid',
        'description': 'Uses SerpAPI service with the official Python library'
    },
    'applescript_safari': {
        'class': ApplescriptSafari,
        'type': 'free',
        'description': 'Uses Safari and AppleScript to access Google Trends'
    },
    'dummy': {
        'class': DummyApi,
        'type': 'free',
        'description': 'Generates dummy data for testing and development'
    }
}

# later I will add selenium, pytrends, and serpapi_raw to the available_apis dictionary

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
__all__ = ['SerpApi', 'SerpWow', 'SearchApi', 'TrendsPy', 'SerpApiPy', 'DummyApi', 'available_apis', 
           'get_free_apis', 'get_paid_apis', 'get_api_info',
           'make_time_range', 'change_tor_identity', 'standard_dict_to_df']

# Note: As far as I can tell, SerpApi and SearchApi always return the same data.
# Note that trendspy is very easily rate-limited, enough so that it might not even be usable.