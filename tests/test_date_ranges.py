import pytest
from datetime import datetime, timedelta
import os
import sys

# Get the absolute path to the gtrend_api_tools directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
#sys.path.insert(0, parent_dir)

# Import directly from the source file
sys.path.insert(0, os.path.join(parent_dir, 'gtrend_api_tools'))
from date_ranges import DateRange

def test_init():
    """Test DateRange initialization"""
    print("Running test: Basic initialization")
    dr = DateRange()
    assert dr.original_date_str is None
    assert dr.start_date is None
    assert dr.end_date is None
    assert dr.start_date_dt is None
    assert dr.end_date_dt is None
    assert dr.start_incomplete is True
    assert dr.end_incomplete is True
    assert dr.formatted_range_ymd is None
    assert dr.formatted_range_mdy is None
    assert dr.granularity == 'D'
    print("PASSED: Basic initialization")

def test_from_dt_single():
    """Test creating DateRange from a single datetime"""
    print("Running test: Single datetime")
    dt = datetime(2024, 3, 21, 14, 30, 45)
    dr = DateRange.from_dt(dt)
    
    assert dr.original_date_str == dt.isoformat()
    assert dr.start_date_dt == datetime(2024, 3, 21)  # Time components zeroed out due to 'D' granularity
    assert dr.start_incomplete is False
    assert dr.end_incomplete is True
    assert dr.formatted_range_ymd == "2024-03-21"
    assert dr.formatted_range_mdy == "03/21/2024"
    print("PASSED: Single datetime")

def test_from_dt_pair():
    """Test creating DateRange from a pair of datetimes"""
    print("Running test: Pair of datetimes")
    start = datetime(2024, 3, 21, 14, 30, 45)
    end = datetime(2024, 3, 28, 14, 30, 45)
    dr = DateRange.from_dt([start, end])
    
    assert dr.original_date_str == f"{start.isoformat()} {end.isoformat()}"
    assert dr.start_date_dt == start.replace(hour=0, minute=0, second=0, microsecond=0)
    assert dr.end_date_dt == end.replace(hour=0, minute=0, second=0, microsecond=0)
    assert dr.start_incomplete is False
    assert dr.end_incomplete is False
    assert dr.formatted_range_ymd == "2024-03-21 2024-03-28"
    assert dr.formatted_range_mdy == "03/21/2024 03/28/2024"
    print("PASSED: Pair of datetimes")

def test_from_dt_invalid():
    """Test creating DateRange with invalid datetime input"""
    print("Running test: Invalid datetime input")
    with pytest.raises(ValueError, match="Input must be either a datetime object or a list/tuple of exactly two datetime objects"):
        DateRange.from_dt("invalid")
    
    with pytest.raises(ValueError):
        DateRange.from_dt([datetime.now()])  # Single item list
    
    with pytest.raises(ValueError):
        DateRange.from_dt([datetime.now(), "invalid"])  # Invalid second item
    print("PASSED: Invalid datetime input")

def test_make_time_range_no_dates():
    """Test make_time_range with no dates provided"""
    print("Running test: No dates provided")
    dr = DateRange()
    with pytest.raises(ValueError, match="At least one date must be provided"):
        dr.make_time_range()
    print("PASSED: No dates provided")

def test_make_time_range_granularity_seconds():
    """Test make_time_range with seconds granularity"""
    print("Running test: Seconds granularity")
    dr = DateRange()
    dr.granularity = 's'
    
    start = datetime(2024, 3, 21, 14, 30, 45, 123456)
    end = datetime(2024, 3, 21, 14, 30, 46, 789012)
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    assert dr.start_date_dt == datetime(2024, 3, 21, 14, 30, 45)
    assert dr.end_date_dt == datetime(2024, 3, 21, 14, 30, 46)
    assert dr.formatted_start_date_ymd == "2024-03-21T14:30:45"
    assert dr.formatted_start_date_mdy == "03/21/2024T14:30:45"
    assert dr.formatted_end_date_ymd == "2024-03-21T14:30:46"
    assert dr.formatted_end_date_mdy == "03/21/2024T14:30:46"
    print("PASSED: Seconds granularity")

def test_make_time_range_granularity_minutes():
    """Test make_time_range with minutes granularity"""
    print("Running test: Minutes granularity")
    dr = DateRange()
    dr.granularity = 'm'
    
    start = datetime(2024, 3, 21, 14, 30, 45)
    end = datetime(2024, 3, 21, 14, 31, 15)
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    assert dr.start_date_dt == datetime(2024, 3, 21, 14, 30)
    assert dr.end_date_dt == datetime(2024, 3, 21, 14, 31)
    assert dr.formatted_start_date_ymd == "2024-03-21T14:30"
    assert dr.formatted_start_date_mdy == "03/21/2024T14:30"
    assert dr.formatted_end_date_ymd == "2024-03-21T14:31"
    assert dr.formatted_end_date_mdy == "03/21/2024T14:31"
    print("PASSED: Minutes granularity")

def test_make_time_range_granularity_hours():
    """Test make_time_range with hours granularity"""
    print("Running test: Hours granularity")
    dr = DateRange()
    dr.granularity = 'h'
    
    start = datetime(2024, 3, 21, 14, 30, 45)
    end = datetime(2024, 3, 21, 15, 20, 30)
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    assert dr.start_date_dt == datetime(2024, 3, 21, 14)
    assert dr.end_date_dt == datetime(2024, 3, 21, 15)
    assert dr.formatted_start_date_ymd == "2024-03-21T14"
    assert dr.formatted_start_date_mdy == "03/21/2024T14"
    assert dr.formatted_end_date_ymd == "2024-03-21T15"
    assert dr.formatted_end_date_mdy == "03/21/2024T15"
    print("PASSED: Hours granularity")

def test_make_time_range_granularity_days():
    """Test make_time_range with days granularity"""
    print("Running test: Days granularity")
    dr = DateRange()
    dr.granularity = 'D'
    
    start = datetime(2024, 3, 21, 14, 30, 45)
    end = datetime(2024, 3, 22, 15, 20, 30)
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    assert dr.start_date_dt == datetime(2024, 3, 21)
    assert dr.end_date_dt == datetime(2024, 3, 22)
    assert dr.formatted_start_date_ymd == "2024-03-21"
    assert dr.formatted_start_date_mdy == "03/21/2024"
    assert dr.formatted_end_date_ymd == "2024-03-22"
    assert dr.formatted_end_date_mdy == "03/22/2024"
    print("PASSED: Days granularity")

def test_make_time_range_granularity_weeks():
    """Test make_time_range with weeks granularity"""
    print("Running test: Weeks granularity")
    dr = DateRange()
    dr.granularity = 'W'
    
    # Wednesday to Tuesday
    start = datetime(2024, 3, 20, 14, 30, 45)  # Wednesday
    end = datetime(2024, 3, 26, 15, 20, 30)    # Tuesday
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    # Should round to previous Sunday and next Saturday
    assert dr.start_date_dt == datetime(2024, 3, 17)  # Sunday
    assert dr.end_date_dt == datetime(2024, 3, 30)  # Saturday
    assert dr.formatted_start_date_ymd == "2024-03-17"
    assert dr.formatted_start_date_mdy == "03/17/2024"
    assert dr.formatted_end_date_ymd == "2024-03-30"
    assert dr.formatted_end_date_mdy == "03/30/2024"
    print("PASSED: Weeks granularity")

def test_make_time_range_granularity_months():
    """Test make_time_range with months granularity"""
    print("Running test: Months granularity")
    dr = DateRange()
    dr.granularity = 'M'
    
    start = datetime(2024, 3, 15, 14, 30, 45)
    end = datetime(2024, 3, 20, 15, 20, 30)
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    assert dr.start_date_dt == datetime(2024, 3, 1)
    assert dr.end_date_dt == datetime(2024, 3, 31)
    assert dr.formatted_start_date_ymd == "2024-03-01"
    assert dr.formatted_start_date_mdy == "03/01/2024"
    assert dr.formatted_end_date_ymd == "2024-03-31"
    assert dr.formatted_end_date_mdy == "03/31/2024"
    print("PASSED: Months granularity")

def test_make_time_range_granularity_quarters():
    """Test make_time_range with quarters granularity"""
    print("Running test: Quarters granularity")
    dr = DateRange()
    dr.granularity = 'Q'
    
    start = datetime(2024, 2, 15, 14, 30, 45)  # Q1
    end = datetime(2024, 5, 20, 15, 20, 30)    # Q2
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    assert dr.start_date_dt == datetime(2024, 1, 1)   # Start of Q1
    assert dr.end_date_dt == datetime(2024, 6, 30)  # End of Q2
    assert dr.formatted_start_date_ymd == "2024-01-01"
    assert dr.formatted_start_date_mdy == "01/01/2024"
    assert dr.formatted_end_date_ymd == "2024-06-30"
    assert dr.formatted_end_date_mdy == "06/30/2024"
    print("PASSED: Quarters granularity")

def test_make_time_range_granularity_years():
    """Test make_time_range with years granularity"""
    print("Running test: Years granularity")
    dr = DateRange()
    dr.granularity = 'Y'
    
    start = datetime(2024, 3, 15, 14, 30, 45)
    end = datetime(2024, 8, 20, 15, 20, 30)
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    assert dr.start_date_dt == datetime(2024, 1, 1)
    assert dr.end_date_dt == datetime(2024, 12, 31)
    assert dr.formatted_start_date_ymd == "2024-01-01"
    assert dr.formatted_start_date_mdy == "01/01/2024"
    assert dr.formatted_end_date_ymd == "2024-12-31"
    assert dr.formatted_end_date_mdy == "12/31/2024"
    print("PASSED: Years granularity")

def test_make_time_range_granularity_decades():
    """Test make_time_range with decades granularity"""
    print("Running test: Decades granularity")
    dr = DateRange()
    dr.granularity = 'X'
    
    start = datetime(2024, 3, 15, 14, 30, 45)
    end = datetime(2028, 8, 20, 15, 20, 30)
    
    dr.make_time_range(start, end)
    
    assert dr.original_date_str is None  # Not set by make_time_range
    assert dr.start_date_dt == datetime(2020, 1, 1)
    assert dr.end_date_dt == datetime(2029, 12, 31)
    assert dr.formatted_start_date_ymd == "2020-01-01"
    assert dr.formatted_start_date_mdy == "01/01/2020"
    assert dr.formatted_end_date_ymd == "2029-12-31"
    assert dr.formatted_end_date_mdy == "12/31/2029"
    print("PASSED: Decades granularity")

def test_make_time_range_invalid_granularity():
    """Test make_time_range with invalid granularity"""
    print("Running test: Invalid granularity")
    dr = DateRange()
    dr.granularity = 'invalid'
    
    with pytest.raises(ValueError, match="Invalid granularity"):
        dr.make_time_range(datetime.now())
    print("PASSED: Invalid granularity")

def test_make_time_range_string_dates():
    """Test make_time_range with string dates"""
    print("Running test: String dates")
    dr = DateRange()
    
    dr.make_time_range("2024-03-21", "2024-03-28")
    
    assert dr.start_date_dt == datetime(2024, 3, 21)
    assert dr.end_date_dt == datetime(2024, 3, 28)
    print("PASSED: String dates")

def test_make_time_range_method_chaining():
    """Test make_time_range method chaining"""
    print("Running test: Method chaining")
    dr = DateRange()
    result = dr.make_time_range(datetime(2024, 3, 21))
    
    assert result is dr
    assert dr.formatted_range_ymd == "2024-03-21"
    assert dr.formatted_range_mdy == "03/21/2024"
    print("PASSED: Method chaining")

def test_standardize_date_str():
    """Test date string standardization"""
    print("Running test: Date string standardization")
    dr = DateRange()
    dr._init_from_str("Mar 21 - 28, 2024")
    
    assert dr.start_date_dt == datetime(2024, 3, 21)
    assert dr.end_date_dt == datetime(2024, 3, 28)
    assert dr.start_incomplete is False
    assert dr.end_incomplete is False
    assert dr.formatted_range_ymd == "2024-03-21 2024-03-28"
    assert dr.formatted_range_mdy == "03/21/2024 03/28/2024"
    print("PASSED: Date string standardization")

def test_standardize_date_str_single_date():
    """Test date string standardization with single date"""
    print("Running test: Single date string")
    dr = DateRange()
    dr._init_from_str("Mar 21, 2024")
    
    assert dr.start_date_dt == datetime(2024, 3, 21)
    assert dr.end_date_dt is None
    assert dr.start_incomplete is False
    assert dr.end_incomplete is True
    assert dr.formatted_range_ymd == "2024-03-21"
    assert dr.formatted_range_mdy == "03/21/2024"
    print("PASSED: Single date string")

def test_standardize_date_str_invalid():
    """Test date string standardization with invalid input"""
    print("Running test: Invalid date string")
    dr = DateRange()
    with pytest.raises(ValueError):
        dr._init_from_str("invalid date")
    print("PASSED: Invalid date string")

def test_from_str_granularity():
    """Test from_str with different granularities"""
    print("Running test: from_str granularity")
    
    # Test daily granularity (default)
    dr = DateRange.from_str("2024-03-21")
    assert dr.granularity == 'D'
    assert dr.start_date_dt.hour == 0
    assert dr.start_date_dt.minute == 0
    assert dr.start_date_dt.second == 0
    
    # Test hourly granularity
    dr = DateRange.from_str("2024-03-21", granularity='hourly')
    assert dr.granularity == 'h'
    assert dr.start_date_dt.hour == 0  # Still 0 because we don't have time in the string
    
    # Test minute granularity
    dr = DateRange.from_str("2024-03-21", granularity='minute')
    assert dr.granularity == 'm'
    assert dr.start_date_dt.minute == 0  # Still 0 because we don't have time in the string
    
    print("PASSED: from_str granularity")

def test_from_dt_granularity():
    """Test from_dt with different granularities"""
    print("Running test: from_dt granularity")
    
    # Test daily granularity (default)
    dt = datetime(2024, 3, 21, 14, 30, 45)
    dr = DateRange.from_dt(dt)
    assert dr.granularity == 'D'
    assert dr.start_date_dt.hour == 0
    assert dr.start_date_dt.minute == 0
    assert dr.start_date_dt.second == 0
    
    # Test hourly granularity
    dr = DateRange.from_dt(dt, granularity='hourly')
    assert dr.granularity == 'h'
    assert dr.start_date_dt.hour == 14
    assert dr.start_date_dt.minute == 0
    assert dr.start_date_dt.second == 0
    
    # Test minute granularity
    dr = DateRange.from_dt(dt, granularity='minute')
    assert dr.granularity == 'm'
    assert dr.start_date_dt.hour == 14
    assert dr.start_date_dt.minute == 30
    assert dr.start_date_dt.second == 0
    
    # Test second granularity
    dr = DateRange.from_dt(dt, granularity='second')
    assert dr.granularity == 's'
    assert dr.start_date_dt.hour == 14
    assert dr.start_date_dt.minute == 30
    assert dr.start_date_dt.second == 45
    
    print("PASSED: from_dt granularity") 