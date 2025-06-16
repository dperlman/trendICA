import time
import requests
from datetime import datetime, timedelta
from typing import Union, List, Optional, Dict, Any
from gtrend_api_tools.APIs.date_ranges import DateRange
from gtrend_api_tools.APIs.base_classes import API_Call
import pandas as pd

class Serpwow(API_Call):
    def __init__(
        self,
        api_key: str,
        api_endpoint: Optional[str] = "https://api.serpwow.com/live/search",
        **kwargs
    ):
        """
        Initialize the Serpwow class.
        
        Args:
            api_key (str): Your Serpwow API key
            api_endpoint (Optional[str]): The API endpoint URL. Defaults to "https://api.serpwow.com/live/search"
            **kwargs: Additional keyword arguments passed to API_Call
        """
        super().__init__(api_key=api_key, api_endpoint=api_endpoint, **kwargs)

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> 'Serpwow':
        """
        Search Google Trends using the Serpwow API.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            
        Returns:
            Serpwow: Returns self for method chaining
        """
        # Store search specification
        self.search_spec = {
            'terms': search_term,
            'start_date': start_date,
            'end_date': end_date,
            'geo': self.geo,
            'language': self.language,
            'cat': self.cat,
            'gprop': self.gprop,
            'region': self.region
        }
        
        self.print_func(f"Sending Serpwow search request:")
        self.print_func(f"  Search term: {search_term}")
        self.print_func(f"  Start date: {start_date if start_date else 'default'}")
        self.print_func(f"  End date: {end_date if end_date else 'default'}")
        
        try:
            # Parse time range if provided
            dr = DateRange(start_date, end_date)
            time_period_min = dr.formatted_range_mdy.split()[0]
            time_period_max = dr.formatted_range_mdy.split()[1]
            
            # Set up the request parameters
            params = {
                'api_key': self.api_key,
                'engine': 'google',
                'search_type': 'trends',
                'q': search_term,
                'data_type': 'INTEREST_OVER_TIME',
                'time_period': 'custom',
                'time_period_min': time_period_min,
                'time_period_max': time_period_max,
                'trends_geo': self.geo,
                'trends_tz': str(self.tz),
                'hl': self.language
            }
            
            # Add optional parameters if they exist and are not None
            if hasattr(self, 'cat') and self.cat is not None:
                params['trends_category'] = str(self.cat)
            if hasattr(self, 'region') and self.region is not None:
                params['trends_region'] = self.region
            if hasattr(self, 'gprop') and self.gprop is not None:
                params['trends_gprop'] = self.gprop
            
            # Make the HTTP GET request
            response = requests.get(self.api_endpoint, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Parse the JSON response
            self.raw_data = response.json()
            
            self.print_func("  Search successful!")
            #self.print_func(self.raw_data)
            
            return self
                    
        except Exception as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise

    def standardize_data(self) -> 'Serpwow':
        """
        Standardize the raw data into a common format.
        Transforms the trends_interest_over_time data into a list of dictionaries with date and values.
        
        Returns:
            Serpwow: Returns self for method chaining
        """
        if not hasattr(self, 'raw_data') or not self.raw_data:
            raise ValueError("No raw data available. Call search() first.")
            
        if 'trends_interest_over_time' not in self.raw_data:
            raise ValueError("Raw data does not contain trends_interest_over_time data")
            
        # Extract the timeline data
        timeline = self.raw_data['trends_interest_over_time']['data']
        
        # Transform the data into the standardized format
        self.data = []
        for entry in timeline:
            dr = DateRange(entry['date_formatted'])
            standardized_entry = {
                'date': dr.formatted_range_ymd,
                'values': [
                    {
                        'value': item['value'],
                        'query': item['keyword']
                    }
                    for item in entry['values']
                ]
            }
            self.data.append(standardized_entry)
            
        return self

def search_serpwow(
    search_term: Union[str, List[str]],
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> Union[pd.DataFrame, Dict[str, Any]]:
    """
    Search Google Trends using the Serpwow API.
    
    Args:
        search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
        start_date (Optional[Union[str, datetime]]): Start date for the search
        end_date (Optional[Union[str, datetime]]): End date for the search
        api_key (Optional[str]): The Serpwow API key. If None, will try to get from environment variable SERPWOW_API_KEY
        **kwargs: Additional keyword arguments passed to API_Call
        
    Returns:
        Union[pd.DataFrame, Dict[str, Any]]: Standardized search results
    """
    serp = Serpwow(**locals())
    return serp.search(search_term, start_date, end_date).standardize_data().data 