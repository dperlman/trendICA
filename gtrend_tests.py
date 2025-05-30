import pytest
import pandas as pd
from datetime import datetime, timedelta
from gtrend import calculate_search_granularity, get_index_granularity

# Test cases for get_index_granularity
@pytest.mark.parametrize("index,expected", [
    # Hourly granularity
    (pd.date_range(start='2024-01-01', periods=24, freq='h'), 'h'),
    # Daily granularity
    (pd.date_range(start='2024-01-01', periods=30, freq='D'), 'D'),
    # Weekly granularity
    (pd.date_range(start='2024-01-01', periods=12, freq='W'), 'W'),
    # Month-end granularity
    (pd.date_range(start='2024-01-01', periods=12, freq='ME'), 'ME'),
    # Empty index (should default to daily)
    (pd.DatetimeIndex([]), 'D'),
    # Single point (should default to daily)
    (pd.DatetimeIndex(['2024-01-01']), 'D'),
])
def test_get_index_granularity(index, expected):
    """Test get_index_granularity with various datetime indices."""
    assert get_index_granularity(index) == expected

def test_get_index_granularity_inferred():
    """Test get_index_granularity with inferred frequencies."""
    # Create an index with hourly data but no explicit frequency
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(24)]
    index = pd.DatetimeIndex(dates)
    assert get_index_granularity(index) == 'h'

    # Create an index with daily data but no explicit frequency
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(30)]
    index = pd.DatetimeIndex(dates)
    assert get_index_granularity(index) == 'D'

# Test cases for calculate_search_granularity
@pytest.mark.parametrize("start_date,end_date,expected_granularity", [
    # Less than 270 days (should use daily)
    ('2024-01-01', '2024-06-01', 'D'),
    # Exactly 270 days (should use daily)
    ('2024-01-01', '2024-09-27', 'D'),
    # Between 270 and 365 days (should use weekly)
    ('2024-01-01', '2024-10-01', 'W'),
    # More than 365 days (should use month-end)
    ('2024-01-01', '2025-01-01', 'ME'),
])
def test_calculate_search_granularity(start_date, end_date, expected_granularity):
    """Test calculate_search_granularity with various date ranges."""
    result = calculate_search_granularity(start_date, end_date)
    assert result['granularity'] == expected_granularity
    assert isinstance(result['index'], pd.DatetimeIndex)
    assert len(result['index']) > 0

def test_calculate_search_granularity_with_datetime():
    """Test calculate_search_granularity with datetime objects."""
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 6, 1)
    result = calculate_search_granularity(start_date, end_date)
    assert result['granularity'] == 'D'
    assert isinstance(result['index'], pd.DatetimeIndex)
    assert len(result['index']) > 0

def test_calculate_search_granularity_edge_cases():
    """Test calculate_search_granularity with edge cases."""
    # Same day
    result = calculate_search_granularity('2024-01-01', '2024-01-01')
    assert result['granularity'] == 'D'
    assert len(result['index']) == 1

    # Very long range
    result = calculate_search_granularity('2020-01-01', '2024-01-01')
    assert result['granularity'] == 'ME'
    assert len(result['index']) > 0

if __name__ == '__main__':
    pytest.main(['-v']) 