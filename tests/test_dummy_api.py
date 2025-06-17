import pytest
from datetime import datetime

@pytest.mark.parametrize('api_key,api_instance', [('dummy_api', 'dummy_api')], indirect=True)
def test_dummy_api_single_term(api_instance, test_dates):
    """Test DummyApi with a single search term."""
    dates = test_dates['short_range']
    search_term = "test"
    
    result = api_instance.search(search_term, dates['start'], dates['end'])
    
    # Debug prints
    print("\nRaw data structure:")
    print(f"Type of result.data: {type(result.data)}")
    print(f"First entry in result.data: {result.data[0] if result.data else 'No data'}")
    print(f"Length of result.data: {len(result.data)}")
    if result.data:
        print(f"Keys in first entry: {result.data[0].keys() if isinstance(result.data[0], dict) else 'Not a dict'}")
    
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
    assert df.index[0] == datetime.strptime(dates['start'], "%Y-%m-%d")
    assert df.index[-1] == datetime.strptime(dates['end'], "%Y-%m-%d")

@pytest.mark.parametrize('api_key,api_instance', [('dummy_api', 'dummy_api')], indirect=True)
def test_dummy_api_multiple_terms(api_instance, test_dates):
    """Test DummyApi with multiple search terms."""
    dates = test_dates['medium_range']
    search_terms = ["term1", "term2", "term3"]
    
    result = api_instance.search(search_terms, dates['start'], dates['end'])
    
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
    assert df.index[0] == datetime.strptime(dates['start'], "%Y-%m-%d")
    assert df.index[-1] == datetime.strptime(dates['end'], "%Y-%m-%d")

@pytest.mark.parametrize('api_key,api_instance', [('dummy_api', 'dummy_api')], indirect=True)
def test_dummy_api_constant_value(api_instance):
    """Test DummyApi with constant fill value."""
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

@pytest.mark.parametrize('api_key,api_instance', [('dummy_api', 'dummy_api')], indirect=True)
def test_dummy_api_datetime_input(api_instance, test_dates):
    """Test DummyApi with datetime objects as input."""
    dates = test_dates['datetime_range']
    search_term = "test"
    
    result = api_instance.search(search_term, dates['start'], dates['end'])
    
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
    assert df.index[0] == dates['start']
    assert df.index[-1] == dates['end']

@pytest.mark.parametrize('api_key,api_instance', [('dummy_api', 'dummy_api')], indirect=True)
def test_dummy_api_search_history(api_instance):
    """Test that search history is properly maintained."""
    start_date = "2024-01-01"
    end_date = "2024-01-02"
    search_term = "hamburger"
    search_term_2 = "pizza"
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