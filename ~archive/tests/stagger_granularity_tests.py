import pytest
from datetime import datetime, timedelta
from gtrend import Trends
from utils import get_index_granularity
import pandas as pd

# Test configuration
START_DATE = datetime(2010, 1, 1, 0, 0, 0)  # Fixed start date
DAY_DURATIONS = [6, 7, 8, 269, 270, 271, 1899, 1900, 1901]  # Test different durations
APIS_TO_TEST = [
    'serpapi'  # Test with SerpAPI
]
DUMMY_API = 'dummy'
VERBOSE = True
STAGGER = 1  # Number of overlapping intervals

def get_dummy_baseline(days: int) -> tuple[int, str]:
    """
    Get the baseline number of records and granularity from dummy API for a given duration
    
    Returns:
        tuple[int, str]: (number of records, granularity)
    """
    dummy_trends = Trends(api=DUMMY_API, verbose=VERBOSE)
    end_date = START_DATE + timedelta(days=days)
    dummy_trends.search(
        search_term="test",
        start_date=START_DATE,
        end_date=end_date,
        stagger=STAGGER
    ).standardize_data().make_dataframe()
    return len(dummy_trends.df), get_index_granularity(dummy_trends.df.index)

def id_func(param):
    """Generate test ID that includes granularity info"""
    if isinstance(param, str):  # api_name
        return param
    else:  # days
        # Get the baseline for this duration
        records, granularity = get_dummy_baseline(param)
        return f"{param}days-{records}rec-{granularity}"

@pytest.mark.parametrize("api_name", APIS_TO_TEST, ids=id_func)
@pytest.mark.parametrize("days", DAY_DURATIONS, ids=id_func)
def test_granularity_consistency(api_name: str, days: int):
    """
    Test that the API returns the same number of records and granularity as dummy_api for a specific duration.
    
    Args:
        api_name (str): Name of the API to test
        days (int): Number of days to test
    """
    # Get baseline from dummy API
    dummy_records, dummy_granularity = get_dummy_baseline(days)
    
    # Test the actual API
    trends = Trends(api=api_name, verbose=VERBOSE)
    end_date = START_DATE + timedelta(days=days)
    
    trends.search(
        search_term="test",
        start_date=START_DATE,
        end_date=end_date,
        stagger=STAGGER
    ).standardize_data().make_dataframe()
    
    api_records = len(trends.df)
    api_granularity = get_index_granularity(trends.df.index)
    
    # Test record count
    assert api_records == dummy_records, \
        f"{api_name} returned {api_records} records for {days} days, " \
        f"but dummy_api returned {dummy_records} records"
    
    # Test granularity
    assert api_granularity == dummy_granularity, \
        f"{api_name} returned {api_granularity} granularity for {days} days, " \
        f"but dummy_api returned {dummy_granularity} granularity" 