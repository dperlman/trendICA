import pytest
import os
import sys
from datetime import datetime, timedelta

# Configuration - Set the API to test here
API_TO_TEST = 'serpapi'  # Change this to test different APIs (e.g., 'serpapi', 'applescript_safari')

# Get the absolute path to the gtrend_api_tools directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
source_dir = os.path.join(parent_dir, 'gtrend_api_tools')
apis_dir = os.path.join(source_dir, 'APIs')

# Add all necessary directories to Python path
sys.path.insert(0, parent_dir)
sys.path.insert(0, source_dir)
sys.path.insert(0, apis_dir)

# Import directly from source files using full paths
import importlib.util

def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import the modules we need in dependency order
utils = import_from_file('utils', os.path.join(source_dir, 'utils.py'))
api_utils = import_from_file('api_utils', os.path.join(apis_dir, 'api_utils.py'))
base_classes = import_from_file('base_classes', os.path.join(apis_dir, 'base_classes.py'))

# Import the specific API module
api_module = import_from_file(API_TO_TEST, os.path.join(apis_dir, f'{API_TO_TEST}.py'))

# Get the classes/functions we need
_print_if_verbose = utils._print_if_verbose
load_config = utils.load_config
API_Call = base_classes.API_Call
ApiClass = getattr(api_module, api_utils.get_api_class_name(f'{API_TO_TEST}.py'))

@pytest.fixture
def api_instance():
    """Create an API instance for testing."""
    return ApiClass()

def test_api_single_term(api_instance):
    """Test API with a single search term."""
    # Test with a 7-day range
    start_date = "2024-01-01"
    end_date = "2024-01-07"
    search_term = "test"
    
    result = api_instance.search(search_term, start_date, end_date)
    
    # Check raw_data and data
    assert len(result.raw_data) == 7  # 7 days
    assert len(result.data) == 7
    assert all(len(entry['values']) == 1 for entry in result.data)  # One term per entry
    
    # Create DataFrame
    result.standardize_data().make_dataframe()
    
    # Check dataframe
    df = result.dataframe
    assert len(df) == 7  # 7 days
    assert len(df.columns) == 1  # One term
    assert df.index[0] == datetime.strptime(start_date, "%Y-%m-%d")
    assert df.index[-1] == datetime.strptime(end_date, "%Y-%m-%d")

def test_api_multiple_terms(api_instance):
    """Test API with multiple search terms."""
    start_date = "2024-01-01"
    end_date = "2024-01-10"
    search_terms = ["term1", "term2", "term3"]
    
    result = api_instance.search(search_terms, start_date, end_date)
    
    # Check raw_data and data
    assert len(result.raw_data) == 10  # 10 days
    assert len(result.data) == 10
    assert all(len(entry['values']) == 3 for entry in result.data)  # Three terms per entry
    
    # Create DataFrame
    result.standardize_data().make_dataframe()
    
    # Check dataframe
    df = result.dataframe
    assert len(df) == 10  # 10 days
    assert len(df.columns) == 3  # Three terms
    assert df.index[0] == datetime.strptime(start_date, "%Y-%m-%d")
    assert df.index[-1] == datetime.strptime(end_date, "%Y-%m-%d")

def test_api_constant_value(api_instance):
    """Test API with constant fill value."""
    start_date = "2024-01-01"
    end_date = "2024-01-05"
    search_terms = ["term1", "term2"]
    fill_value = 42
    
    result = api_instance.search(search_terms, start_date, end_date, fill_value=fill_value)
    
    # Check raw_data and data
    assert len(result.raw_data) == 5  # 5 days
    assert len(result.data) == 5
    assert all(len(entry['values']) == 2 for entry in result.data)  # Two terms per entry
    assert all(all(v['value'] == fill_value for v in entry['values']) for entry in result.data)
    
    # Create DataFrame
    result.standardize_data().make_dataframe()
    
    # Check dataframe
    df = result.dataframe
    assert len(df) == 5  # 5 days
    assert len(df.columns) == 2  # Two terms
    assert (df == fill_value).all().all()  # All values should be fill_value

def test_api_datetime_input(api_instance):
    """Test API with datetime objects as input."""
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 3)
    search_term = "test"
    
    result = api_instance.search(search_term, start_date, end_date)
    
    # Check raw_data and data
    assert len(result.raw_data) == 3  # 3 days
    assert len(result.data) == 3
    assert all(len(entry['values']) == 1 for entry in result.data)
    
    # Create DataFrame
    result.standardize_data().make_dataframe()
    
    # Check dataframe
    df = result.dataframe
    assert len(df) == 3  # 3 days
    assert len(df.columns) == 1  # One term
    assert df.index[0] == start_date
    assert df.index[-1] == end_date

def test_api_search_history(api_instance):
    """Test that search history is properly maintained."""
    start_date = "2024-01-01"
    end_date = "2024-01-02"
    search_term = "test"
    search_term_2 = "test2"
    fill_value = 100
    
    # First search
    result1 = api_instance.search(search_term, start_date, end_date, fill_value=fill_value)
    assert len(api_instance.search_history) == 1
    assert api_instance.search_history[0].terms == [search_term]
    assert api_instance.search_history[0].start_date == start_date
    assert api_instance.search_history[0].end_date == end_date
    
    # Second search
    result2 = api_instance.search(search_term_2, "2024-01-03", "2024-01-04")
    assert len(api_instance.search_history) == 2
    assert api_instance.search_history[1].terms == [search_term_2]