"""
Configuration-related test fixtures for gtrend_api_tools.
"""
import os
import pytest
import yaml

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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