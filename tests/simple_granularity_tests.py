import os
import sys

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pytest
from datetime import datetime, timedelta
from gtrend_api_tools import Trends
from gtrend_api_tools.utils import get_index_granularity
import pandas as pd
from typing import Optional

# Test configuration
START_DATE = datetime(2010, 1, 1, 0, 0, 0)  # Fixed start date
DAY_DURATIONS = [6, 7, 8, 269, 270, 271, 1899, 1900, 1901]  # Test different durations
APIS_TO_TEST = [
    'serpapi'  # Test with SerpAPI
]
DUMMY_API = 'dummy'
LOG_LEVEL = 'INFO'  # Changed from VERBOSE boolean to logging level

# Dictionary to store Trends instances
_trends_instances = {}

@pytest.fixture(scope="module")
def trends_instance(request):
    """Fixture that creates and yields a Trends instance for the specified API"""
    api_name = request.param
    
    # Create instance if it doesn't exist for this API
    if api_name not in _trends_instances:
        _trends_instances[api_name] = Trends(use_api=api_name, verbose=LOG_LEVEL)
    
    return _trends_instances[api_name]

def get_dummy_baseline(days: int, granularity: Optional[str] = None) -> tuple[int, str]:
    """
    Get the baseline number of records and granularity from dummy API for a given duration
    
    Args:
        days (int): Number of days to test
        granularity (Optional[str]): Specific granularity to test. If None, uses default behavior.
    
    Returns:
        tuple[int, str]: (number of records, granularity)
    """
    dummy_trends = Trends(use_api=DUMMY_API, verbose=LOG_LEVEL)
    end_date = START_DATE + timedelta(days=days)
    dummy_trends.search(
        search_term="test",
        start_date=START_DATE,
        end_date=end_date,
        granularity=granularity
    ).standardize_data().make_dataframe()
    return len(dummy_trends.data), get_index_granularity(dummy_trends.df.index)

# Pre-calculate baselines for all durations to avoid recursion
BASELINES = {days: get_dummy_baseline(days) for days in DAY_DURATIONS}

def id_func(param):
    """Generate test ID that includes granularity info"""
    if isinstance(param, str):  # api_name
        return param
    elif isinstance(param, tuple):  # (days, granularity)
        days, granularity = param
        # Get the pre-calculated baseline for this duration and granularity
        records, actual_granularity = get_dummy_baseline(days, granularity)
        print(f"✓ {days} days, {granularity} granularity: {records} records, {actual_granularity} actual granularity")
        return f"{days}days-{granularity}-{records}rec-{actual_granularity}"
    else:  # days
        # Get the pre-calculated baseline for this duration
        records, granularity = BASELINES[param]
        print(f"✓ {param} days: {records} records, {granularity} granularity")
        return f"{param}days-{records}rec-{granularity}"

@pytest.fixture
def search_results(trends_instance: Trends, days: int):
    """
    Function-scoped fixture that performs a search using the module-scoped trends_instance.
    This avoids duplicating the search operation between tests while maintaining test isolation.
    
    Args:
        trends_instance (Trends): The module-scoped Trends instance to use for the search
        days (int): Number of days to test
    
    Returns:
        Trends: The Trends instance with search results
    """
    end_date = START_DATE + timedelta(days=days)
    trends_instance.search(
        search_term="test",
        start_date=START_DATE,
        end_date=end_date
    ).standardize_data().make_dataframe()
    return trends_instance

@pytest.mark.parametrize("trends_instance", APIS_TO_TEST, indirect=True, ids=id_func)
@pytest.mark.parametrize("days", DAY_DURATIONS, ids=id_func)
def test_record_count_consistency(search_results: Trends, days: int):
    """
    Test that the API returns the same number of records as dummy_api for a specific duration.
    This test verifies the default behavior when no granularity is specified.
    
    Args:
        search_results (Trends): The Trends instance with search results
        days (int): Number of days to test
    """
    # Get baseline from pre-calculated values
    dummy_records, _ = BASELINES[days]
    
    api_records = len(search_results.data)
    
    assert api_records == dummy_records, \
        f"API returned {api_records} records for {days} days, " \
        f"but dummy_api returned {dummy_records} records"
    
    print(f"✓ {days} days: {api_records} records")

@pytest.mark.parametrize("trends_instance", APIS_TO_TEST, indirect=True, ids=id_func)
@pytest.mark.parametrize("days", DAY_DURATIONS, ids=id_func)
def test_granularity_consistency(search_results: Trends, days: int):
    """
    Test that the API returns the same granularity as dummy_api for a specific duration.
    This test verifies the default behavior when no granularity is specified.
    
    Args:
        search_results (Trends): The Trends instance with search results
        days (int): Number of days to test
    """
    # Get baseline from pre-calculated values
    _, dummy_granularity = BASELINES[days]
    
    api_granularity = get_index_granularity(search_results.df.index)
    
    assert api_granularity == dummy_granularity, \
        f"API returned {api_granularity} granularity for {days} days, " \
        f"but dummy_api returned {dummy_granularity} granularity"
    
    print(f"✓ {days} days: {api_granularity} granularity")

@pytest.mark.parametrize("trends_instance", APIS_TO_TEST, indirect=True, ids=id_func)
@pytest.mark.parametrize("test_case", [
    # Single block tests
    (7, "h"),     # Hourly granularity for 7 days (single block)
    (90, "D"),    # Daily granularity for 90 days (single block)
    (30, "W"),    # Weekly granularity for 30 days (single block)
    (90, "MS"),   # Monthly granularity for 90 days (single block)
    
    # Multi-block tests
    (365, "D"),   # Daily granularity for 365 days (multiple blocks)
    (90, "h"),    # Hourly granularity for 90 days (multiple blocks)
    (365, "W"),   # Weekly granularity for 365 days (multiple blocks)
    (365, "MS"),  # Monthly granularity for 365 days (multiple blocks)
], ids=id_func)
def test_specific_granularity(trends_instance: Trends, test_case: tuple[int, str]):
    """
    Test that the API respects specific granularity requests.
    Tests both single-block and multi-block cases.
    
    Args:
        trends_instance (Trends): The Trends instance to use for testing
        test_case (tuple[int, str]): (days, granularity) to test
    """
    days, granularity = test_case
    
    # Get baseline for this specific granularity
    dummy_records, dummy_granularity = get_dummy_baseline(days, granularity)
    
    # Test the actual API
    end_date = START_DATE + timedelta(days=days)
    
    trends_instance.search(
        search_term="test",
        start_date=START_DATE,
        end_date=end_date,
        granularity=granularity
    ).standardize_data().make_dataframe()
    
    api_records = len(trends_instance.data)
    api_granularity = get_index_granularity(trends_instance.df.index)
    
    # Test record count
    assert api_records == dummy_records, \
        f"API returned {api_records} records for {days} days with {granularity} granularity, " \
        f"but dummy_api returned {dummy_records} records"
    
    # Test granularity
    assert api_granularity == dummy_granularity, \
        f"API returned {api_granularity} granularity for {days} days with {granularity} granularity, " \
        f"but dummy_api returned {dummy_granularity} granularity"
    
    # If we get here, both assertions passed
    print(f"✓ {days} days, {granularity} granularity: {api_records} records, {api_granularity} actual granularity") 