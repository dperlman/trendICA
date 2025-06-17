"""
API-specific test fixtures for gtrend_api_tools.
"""
import os
import sys
import pytest
import yaml
from datetime import datetime

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Test configuration
API_TO_TEST = 'dummy_api'  # Specify which API to test
VERBOSE = False  # Set to True to see detailed API output during tests

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