import pytest
from datetime import datetime
from .conftest import API_TO_TEST

@pytest.mark.parametrize('api_key,api_instance', [(API_TO_TEST, API_TO_TEST)], indirect=True)
def test_api_search_history(api_instance, test_terms, test_dates):
    """Test that search history is properly maintained."""
    start_date_1 = test_dates['short_range']['start']
    end_date_1 = test_dates['short_range']['end']
    start_date_2 = test_dates['medium_range']['start']
    end_date_2 = test_dates['medium_range']['end']

    # First search
    api_instance.search(test_terms['term1'], start_date_1, end_date_1).standardize_data()
    assert api_instance.data
    assert len(api_instance.search_history) == 1
    assert api_instance.search_history[0].terms == [test_terms['term1']]
    
    # Check DataFrame conversion for first search
    api_instance.make_dataframe()
    assert not api_instance.dataframe.empty
    assert test_terms['term1'].replace(' ', '_').lower() in api_instance.dataframe.columns

    # Second search
    api_instance.search(test_terms['term2'], start_date_2, end_date_2).standardize_data()
    assert api_instance.data
    assert len(api_instance.search_history) == 2
    assert api_instance.search_history[1].terms == [test_terms['term2']]
    
    # Check DataFrame conversion for second search
    api_instance.make_dataframe()
    assert not api_instance.dataframe.empty
    assert test_terms['term2'].replace(' ', '_').lower() in api_instance.dataframe.columns

    # Third search
    api_instance.search(test_terms['term3'], start_date_2, end_date_2).standardize_data()
    assert api_instance.data
    assert len(api_instance.search_history) == 3
    assert api_instance.search_history[2].terms == [test_terms['term3']]
    
    # Check DataFrame conversion for third search
    api_instance.make_dataframe()
    assert not api_instance.dataframe.empty
    assert test_terms['term3'].replace(' ', '_').lower() in api_instance.dataframe.columns

@pytest.mark.parametrize('api_key,api_instance', [(API_TO_TEST, API_TO_TEST)], indirect=True)
def test_api_single_term(api_instance, test_terms, test_dates):
    """Test API with a single search term."""
    search_term = test_terms['term1']
    start_date = test_dates['short_range']['start']
    end_date = test_dates['short_range']['end']
    api_instance.search(search_term, start_date, end_date).standardize_data()
    
    # Check standardized data structure
    assert api_instance.data
    assert all(len(entry['values']) == 1 for entry in api_instance.data)  # One term per entry
    assert all(entry['values'][0]['query'] == search_term for entry in api_instance.data)
    
    # Check DataFrame conversion
    api_instance.make_dataframe()
    assert not api_instance.dataframe.empty
    assert len(api_instance.dataframe.columns) == 1  # One column for the single term
    assert search_term.replace(' ', '_').lower() in api_instance.dataframe.columns

@pytest.mark.parametrize('api_key,api_instance', [(API_TO_TEST, API_TO_TEST)], indirect=True)
def test_api_multiple_terms(api_instance, test_terms, test_dates):
    """Test API with multiple search terms."""
    search_terms = [test_terms['term1'], test_terms['term2'], test_terms['term3']]
    start_date = test_dates['short_range']['start']
    end_date = test_dates['short_range']['end']
    api_instance.search(search_terms, start_date, end_date).standardize_data()
    
    # Check standardized data structure
    assert api_instance.data
    assert all(len(entry['values']) == len(search_terms) for entry in api_instance.data)  # All terms per entry
    # Check that all search terms are present in each entry
    for entry in api_instance.data:
        entry_queries = {value['query'] for value in entry['values']}
        assert all(term in entry_queries for term in search_terms)
    
    # Check DataFrame conversion
    api_instance.make_dataframe()
    assert not api_instance.dataframe.empty
    assert len(api_instance.dataframe.columns) == len(search_terms)  # One column per term
    # Check that all search terms are present as columns (with sanitization)
    sanitized_terms = [term.replace(' ', '_').lower() for term in search_terms]
    assert all(term in api_instance.dataframe.columns for term in sanitized_terms)

@pytest.mark.parametrize('api_key,api_instance', [(API_TO_TEST, API_TO_TEST)], indirect=True)
def test_api_datetime_input(api_instance, test_terms, test_dates):
    """Test API with datetime objects as input."""
    search_term = test_terms['term1']
    start_date = test_dates['datetime_range']['start']
    end_date = test_dates['datetime_range']['end']
    api_instance.search(search_term, start_date, end_date).standardize_data()
    
    # Check standardized data structure
    assert api_instance.data
    # Check date range
    dates = [datetime.strptime(entry['date'], "%Y-%m-%d") for entry in api_instance.data]
    assert min(dates) >= start_date
    assert max(dates) <= end_date
    
    # Check DataFrame conversion
    api_instance.make_dataframe()
    assert not api_instance.dataframe.empty
    assert api_instance.dataframe.index[0].to_pydatetime() >= start_date
    assert api_instance.dataframe.index[-1].to_pydatetime() <= end_date

# Test: should raise ValueError when terms is None
@pytest.mark.parametrize('api_key,api_instance', [(API_TO_TEST, API_TO_TEST)], indirect=True)
def test_api_raises_when_terms_none(api_instance, test_dates):
    start_date = test_dates['short_range']['start']
    end_date = test_dates['short_range']['end']
    with pytest.raises(ValueError):
        api_instance.search(None, start_date, end_date)

# Test: should raise ValueError when start_date is None
@pytest.mark.parametrize('api_key,api_instance', [(API_TO_TEST, API_TO_TEST)], indirect=True)
def test_api_raises_when_start_date_none(api_instance, test_terms, test_dates):
    search_term = test_terms['term1']
    end_date = test_dates['short_range']['end']
    with pytest.raises(ValueError):
        api_instance.search(search_term, None, end_date)

# Test: should raise ValueError when end_date is None
@pytest.mark.parametrize('api_key,api_instance', [(API_TO_TEST, API_TO_TEST)], indirect=True)
def test_api_raises_when_end_date_none(api_instance, test_terms, test_dates):
    search_term = test_terms['term1']
    start_date = test_dates['short_range']['start']
    with pytest.raises(ValueError):
        api_instance.search(search_term, start_date, None)

# Test: should raise ValueError when the number of search terms is 6
@pytest.mark.parametrize('api_key,api_instance', [(API_TO_TEST, API_TO_TEST)], indirect=True)
def test_api_raises_when_too_many_terms(api_instance, test_dates, test_config):
    max_terms = test_config['api_parameters']['all']['max_terms']
    search_terms = [f"term{i}" for i in range(max_terms + 1)]
    start_date = test_dates['short_range']['start']
    end_date = test_dates['short_range']['end']
    with pytest.raises(ValueError):
        api_instance.search(search_terms, start_date, end_date)