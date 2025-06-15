import pytest
import pandas as pd
from datetime import datetime, timedelta
from gtrend_api_tools.granularity import GranularityManager
from gtrend_api_tools.utils import load_config

@pytest.fixture
def config():
    """Fixture providing a test configuration."""
    return load_config()

@pytest.fixture
def granularity_manager(config):
    """Fixture providing a GranularityManager instance."""
    return GranularityManager(config)

def test_init_with_config(config):
    """Test initialization with provided config."""
    gm = GranularityManager(config)
    assert isinstance(gm.rules, dict)
    assert len(gm.rules) > 0

def test_init_without_config():
    """Test initialization without config (should raise error)."""
    with pytest.raises(ValueError):
        GranularityManager({})

def test_get_index_granularity_hourly(granularity_manager):
    """Test granularity detection for hourly data."""
    # Create hourly index
    index = pd.date_range(start='2024-01-01', periods=24, freq='h')
    assert granularity_manager.get_index_granularity(index) == 'h'

def test_get_index_granularity_daily(granularity_manager):
    """Test granularity detection for daily data."""
    # Create daily index
    index = pd.date_range(start='2024-01-01', periods=7, freq='D')
    assert granularity_manager.get_index_granularity(index) == 'D'

def test_get_index_granularity_weekly(granularity_manager):
    """Test granularity detection for weekly data."""
    # Create weekly index
    index = pd.date_range(start='2024-01-01', periods=4, freq='W')
    assert granularity_manager.get_index_granularity(index) == 'W'

def test_get_index_granularity_monthly(granularity_manager):
    """Test granularity detection for monthly data."""
    # Create monthly index
    index = pd.date_range(start='2024-01-01', periods=12, freq='M')
    assert granularity_manager.get_index_granularity(index) == 'M'

def test_get_index_granularity_empty(granularity_manager):
    """Test granularity detection with empty index."""
    index = pd.DatetimeIndex([])
    assert granularity_manager.get_index_granularity(index) is None

def test_get_index_granularity_single_point(granularity_manager):
    """Test granularity detection with single data point."""
    index = pd.DatetimeIndex(['2024-01-01'])
    assert granularity_manager.get_index_granularity(index) is None

def test_create_time_indices_hourly(granularity_manager):
    """Test time index creation for hourly data."""
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2024, 1, 1, 23, 0, 0)
    dt_index, period_index = granularity_manager.create_time_indices(start_dt, end_dt, 'h')
    
    assert len(dt_index) == 24
    assert len(period_index) == 24
    assert dt_index.freqstr == 'h'
    assert period_index.freqstr == 'h'

def test_create_time_indices_daily(granularity_manager):
    """Test time index creation for daily data."""
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2024, 1, 7)
    dt_index, period_index = granularity_manager.create_time_indices(start_dt, end_dt, 'D')
    
    assert len(dt_index) == 7
    assert len(period_index) == 7
    assert dt_index.freqstr == 'D'
    assert period_index.freqstr == 'D'

def test_create_time_indices_invalid_granularity(granularity_manager):
    """Test time index creation with invalid granularity."""
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2024, 1, 2)
    with pytest.raises(ValueError):
        granularity_manager.create_time_indices(start_dt, end_dt, 'X')

def test_calculate_total_units_hourly(granularity_manager):
    """Test total units calculation for hourly data."""
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2024, 1, 1, 23, 0, 0)
    assert granularity_manager.calculate_total_units(start_dt, end_dt, 'h') == 24

def test_calculate_total_units_daily(granularity_manager):
    """Test total units calculation for daily data."""
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2024, 1, 7)
    assert granularity_manager.calculate_total_units(start_dt, end_dt, 'D') == 7

def test_calculate_total_units_invalid_granularity(granularity_manager):
    """Test total units calculation with invalid granularity."""
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2024, 1, 2)
    with pytest.raises(ValueError):
        granularity_manager.calculate_total_units(start_dt, end_dt, 'X')

def test_calculate_search_granularity_hourly(granularity_manager):
    """Test search granularity calculation for hourly data."""
    start_date = '2024-01-01'
    end_date = '2024-01-02'
    result = granularity_manager.calculate_search_granularity(start_date, end_date)
    
    assert result['granularity'] == 'h'
    assert len(result['datetime_index']) == 25  # 24 hours + 1
    assert len(result['period_index']) == 25
    assert result['max_units'] == granularity_manager.rules['h']['max_records']
    assert result['blocks'] == 1

def test_calculate_search_granularity_daily(granularity_manager):
    """Test search granularity calculation for daily data."""
    start_date = '2024-01-01'
    end_date = '2024-01-30'
    result = granularity_manager.calculate_search_granularity(start_date, end_date)
    
    assert result['granularity'] == 'D'
    assert len(result['datetime_index']) == 30
    assert len(result['period_index']) == 30
    assert result['max_units'] == granularity_manager.rules['D']['max_records']
    assert result['blocks'] == 1

def test_calculate_search_granularity_with_granularity_param(granularity_manager):
    """Test search granularity calculation with explicit granularity."""
    start_date = '2024-01-01'
    end_date = '2024-01-30'
    result = granularity_manager.calculate_search_granularity(start_date, end_date, granularity='D')
    
    assert result['granularity'] == 'D'
    assert len(result['datetime_index']) == 30
    assert len(result['period_index']) == 30
    assert result['max_units'] == granularity_manager.rules['D']['max_records']
    assert result['blocks'] == 1

def test_calculate_search_granularity_invalid_granularity(granularity_manager):
    """Test search granularity calculation with invalid granularity."""
    start_date = '2024-01-01'
    end_date = '2024-01-02'
    with pytest.raises(ValueError):
        granularity_manager.calculate_search_granularity(start_date, end_date, granularity='X')

def test_calculate_search_granularity_large_range(granularity_manager):
    """Test search granularity calculation for a large date range."""
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    result = granularity_manager.calculate_search_granularity(start_date, end_date)
    
    # Should use monthly granularity for a year-long range
    assert result['granularity'] == 'M'
    assert len(result['datetime_index']) == 13  # 12 months + 1
    assert len(result['period_index']) == 13
    assert result['max_units'] == granularity_manager.rules['M']['max_records']
    assert result['blocks'] == 1

def test_calculate_search_granularity_with_datetime_objects(granularity_manager):
    """Test search granularity calculation with datetime objects."""
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2024, 1, 7)
    result = granularity_manager.calculate_search_granularity(start_dt, end_dt)
    
    assert result['granularity'] == 'D'
    assert len(result['datetime_index']) == 7
    assert len(result['period_index']) == 7
    assert result['max_units'] == granularity_manager.rules['D']['max_records']
    assert result['blocks'] == 1

def test_calculate_search_granularity_with_time_components(granularity_manager):
    """Test search granularity calculation with time components in dates."""
    start_dt = datetime(2024, 1, 1, 12, 30, 45)
    end_dt = datetime(2024, 1, 7, 23, 59, 59)
    result = granularity_manager.calculate_search_granularity(start_dt, end_dt)
    
    # Time components should be truncated
    assert result['granularity'] == 'D'
    assert len(result['datetime_index']) == 7
    assert len(result['period_index']) == 7
    assert result['max_units'] == granularity_manager.rules['D']['max_records']
    assert result['blocks'] == 1 