import time
import requests
from datetime import datetime
from typing import Union, List, Optional, Dict, Any
import pandas as pd
import unicodedata
from .api_utils import make_time_range
from .base_classes import API_Call

class SerpApi(API_Call):
    def __init__(
        self,
        api_key: str,
        api_endpoint: str = "https://serpapi.com/search",
        **kwargs
    ):
        """
        Initialize the SerpAPI class.
        
        Args:
            api_key (str): Your SerpAPI API key
            api_endpoint (str): The SerpAPI endpoint URL
            **kwargs: Additional keyword arguments passed to API_Call
        """
        super().__init__(api_key=api_key, **kwargs)
        self.base_url = api_endpoint

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> 'SerpApi':
        """
        Search Google Trends using the SerpApi.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            
        Returns:
            SerpApi: Returns self for method chaining
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
        
        self.print_func(f"Sending SerpApi search request:")
        self.print_func(f"  Search term: {search_term}")
        self.print_func(f"  Start date: {start_date if start_date else 'default'}")
        self.print_func(f"  End date: {end_date if end_date else 'default'}")
        
        try:
            # Set up the request parameters
            params = {
                'api_key': self.api_key,
                'engine': 'google_trends',
                'q': search_term,
                'geo': self.geo,
                'hl': self.language
            }
            
            # Add optional parameters if they exist and are not None
            if hasattr(self, 'cat') and self.cat is not None:
                params['cat'] = self.cat
            if hasattr(self, 'region') and self.region is not None:
                params['region'] = self.region
            if hasattr(self, 'gprop') and self.gprop is not None:
                params['gprop'] = self.gprop
            
            # Parse time range if provided
            time_range = make_time_range(start_date, end_date)
            params['date'] = time_range['ymd']
            self.print_func(f"  Time range: {time_range['ymd']}")
            
            # Make the API call using requests
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            self.raw_data = response.json()
            
            # Check if there's an error in the results
            if isinstance(self.raw_data, dict) and "error" in self.raw_data:
                error_msg = self.raw_data["error"]
                self.print_func(f"  Search failed: {error_msg}")
                raise Exception(error_msg)
            
            self.print_func("  Search successful!")
            
            return self
                    
        except requests.exceptions.RequestException as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise
        except Exception as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise

    def standardize_data(self) -> 'SerpApi':
        """
        Standardize the raw data into a common format.
        Transforms the interest_over_time data into a list of dictionaries with date and values.
        
        Returns:
            SerpApi: Returns self for method chaining
        """
        if not hasattr(self, 'raw_data') or not self.raw_data:
            raise ValueError("No raw data available. Call search() first.")
            
        if 'interest_over_time' not in self.raw_data:
            raise ValueError("Raw data does not contain interest_over_time data")
            
        # Extract the timeline data
        timeline = self.raw_data['interest_over_time']['timeline_data']
        
        # Transform the data into the standardized format
        self.data = []
        for entry in timeline:
            standardized_entry = {
                'date': unicodedata.normalize('NFKC', entry['date']),
                'values': [
                    {
                        'value': item['extracted_value'],
                        'query': item['query']
                    }
                    for item in entry['values']
                ]
            }
            self.data.append(standardized_entry)
        self.print_func(f"Standardized data length: {len(self.data)}")
        return self

def search_serpapi(
    search_term: Union[str, List[str]],
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> Union[pd.DataFrame, Dict[str, Any]]:
    """
    Search Google Trends using the SerpAPI library.
    
    Args:
        search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
        start_date (Optional[Union[str, datetime]]): Start date for the search
        end_date (Optional[Union[str, datetime]]): End date for the search
        api_key (Optional[str]): The SerpAPI API key. If None, will try to get from environment variable SERPAPI_API_KEY
        **kwargs: Additional keyword arguments passed to API_Call
        
    Returns:
        Union[pd.DataFrame, Dict[str, Any]]: Standardized search results
    """
    serp = SerpApi(**locals())
    return serp.search(search_term, start_date, end_date).standardize_data().data 