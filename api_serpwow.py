import time
import requests
from datetime import datetime, timedelta
from typing import Union, List, Optional, Dict, Any
from utils import make_time_range
from base_classes import API_Call
import pandas as pd

class SerpWow(API_Call):
    def __init__(
        self,
        api_key: str,
        geo: str = "US",
        language: str = "en",
        tz: int = 0,
        verbose: bool = False,
        print_func: Optional[callable] = None,
        **kwargs
    ):
        """
        Initialize the SerpWow class.
        
        Args:
            api_key (str): Your SerpWow API key
            geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
            language (str): Language for the search. Defaults to "en"
            tz (int): Timezone offset in minutes. Defaults to 0
            verbose (bool): Whether to print debug information
            print_func (Optional[callable]): Function to use for printing debug information
            **kwargs: Additional keyword arguments to pass to the SerpWow class
        """
        super().__init__(**locals())
        self.print_func = print_func if print_func is not None else print

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """
        Search Google Trends using the SerpWow API.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            
        Returns:
            Union[pd.DataFrame, Dict[str, Any]]: Raw search results
        """
        self.print_func(f"Sending SerpWow search request:")
        self.print_func(f"  Search term: {search_term}")
        self.print_func(f"  Start date: {start_date if start_date else 'default'}")
        self.print_func(f"  End date: {end_date if end_date else 'default'}")
        
        try:
            # Parse time range if provided
            if start_date or end_date:
                time_range = make_time_range(start_date, end_date)
                start_dt = datetime.strptime(time_range.split()[0], "%Y-%m-%d")
                end_dt = datetime.strptime(time_range.split()[1], "%Y-%m-%d")
                # Convert to SerpWow format (MM/DD/YYYY)
                time_period_min = start_dt.strftime("%m/%d/%Y")
                time_period_max = end_dt.strftime("%m/%d/%Y")
            else:
                # Default to last 90 days if no time range provided
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=90)
                time_period_min = start_dt.strftime("%m/%d/%Y")
                time_period_max = end_dt.strftime("%m/%d/%Y")
            
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
                'trends_language': self.language
            }
            
            # Add any additional parameters from kwargs
            params.update(self.kwargs)
            
            # Make the HTTP GET request
            response = requests.get('https://api.serpwow.com/live/search', params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Parse the JSON response
            data = response.json()
            
            self.print_func("  Search successful!")
            self.print_func(data)
            
            return data
                    
        except Exception as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise

def search_serpwow(
    search_term: Union[str, List[str]],
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    api_key: Optional[str] = None,
    geo: str = "US",
    language: str = "en",
    tz: int = 0,
    no_cache: bool = False,
    cat: Optional[int] = None,
    region: Optional[str] = None,
    verbose: bool = False,
    print_func: Optional[callable] = None,
    **kwargs
) -> Union[pd.DataFrame, Dict[str, Any]]:
    """
    Search Google Trends using the SerpWow API.
    
    Args:
        search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
        start_date (Optional[Union[str, datetime]]): Start date for the search
        end_date (Optional[Union[str, datetime]]): End date for the search
        api_key (Optional[str]): The SerpWow API key. If None, will try to get from environment variable SERPWOW_API_KEY
        geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
        language (str): Language for the search. Defaults to "en"
        tz (int): Timezone offset in minutes. Defaults to 0
        no_cache (bool): Whether to skip the cache. Defaults to False
        cat (Optional[int]): Category for the search. Defaults to None
        region (Optional[str]): Region for the search. Defaults to None
        verbose (bool): Whether to print debug information
        print_func (Optional[callable]): Function to use for printing debug information
        **kwargs: Additional keyword arguments to pass to the SerpWow class
        
    Returns:
        Union[pd.DataFrame, Dict[str, Any]]: Raw search results
    """
    serp = SerpWow(**locals())
    return serp.search(search_term, start_date, end_date) 