"""
Main test configuration and fixture exports for gtrend_api_tools.
"""
import os
import sys
import pytest
import yaml
from datetime import datetime, timedelta

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import and re-export fixtures from submodules
from .fixtures.api_fixtures import API_TO_TEST, VERBOSE, api_key, api_instance
from .fixtures.data_fixtures import test_terms, test_dates
from .fixtures.config_fixtures import test_config, available_apis

# Test configuration
API_TO_TEST = 'dummy_api'  # Specify which API to test
VERBOSE = False  # Set to True to see detailed API output during tests

@pytest.fixture(scope="module")
def test_terms():
    """Provide common test search terms."""
    return {
        'term1': "hamburger",
        'term2': "pizza",
        'term3': "hot dog",
        'term4': "ice cream",
        'term5': "coffee",
        'term6': "tea",
        'term7': "wine",
        'term8': "beer",
        'term9': "soda",
        'term10': "water"
    }

@pytest.fixture(scope="module")
def test_config():
    """Load test configuration."""
    from gtrend_api_tools.utils import load_config
    return load_config()

@pytest.fixture(scope="module")
def available_apis():
    """Load available APIs configuration."""
    available_apis_path = os.path.join(project_root, 'gtrend_api_tools', 'config', 'available_apis.yaml')
    with open(available_apis_path, 'r') as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="module")
def api_key(test_config, request, available_apis):
    """Get API key for the specified API."""
    if not hasattr(request, 'param'):
        pytest.fail("api_key fixture requires parameterization with API name")
    
    api_name = request.param
    # If the API doesn't require a key, return None
    if available_apis.get(api_name, {}).get('type') != 'paid':
        return None
    return test_config.get('api_keys', {}).get(api_name)

@pytest.fixture(scope="module")
def test_dates():
    """Provide common test date ranges."""
    return {
        'short_range': {
            'start': "2024-01-01",
            'end': "2024-01-07"
        },
        'medium_range': {
            'start': "2024-01-01",
            'end': "2024-01-10"
        },
        'datetime_range': {
            'start': datetime(2024, 1, 1),
            'end': datetime(2024, 1, 3)
        }
    }

@pytest.fixture(scope="module")
def api_instance(api_key, available_apis, request):
    """Create an API instance for testing."""
    if not hasattr(request, 'param'):
        pytest.fail("api_instance fixture requires parameterization with API name")
    
    api_name = request.param
    
    # Check if API is paid and requires an API key
    if available_apis.get(api_name, {}).get('type') == 'paid' and not api_key:
        pytest.skip(f"No API key found for {api_name} in config")
    
    # Import the API class
    from gtrend_api_tools.APIs import api_utils
    from importlib import import_module
    
    module = import_module(f'gtrend_api_tools.APIs.{api_name}')
    ApiClass = getattr(module, api_utils.get_api_class_name(f'{api_name}.py'))
    
    return ApiClass(api_key=api_key, verbose=VERBOSE)

def pytest_configure(config):
    """Print the current API being tested before running tests."""
    print(f"\nRunning tests with API: {API_TO_TEST}\n")

# Re-export all fixtures
__all__ = [
    'API_TO_TEST',
    'VERBOSE',
    'api_key',
    'api_instance',
    'test_terms',
    'test_dates',
    'test_config',
    'available_apis'
] 