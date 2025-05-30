import time
import requests
from datetime import datetime
from typing import Union, List, Optional
import pandas as pd
from utils import make_time_range
from base_classes import API_Call

class SerpAPI(API_Call):
    def __init__(
        self,
        api_key: str,
        geo: str = "US",
        language: str = "en",
        verbose: bool = False,
        print_func: Optional[callable] = None,
        **kwargs
    ):
        """
        Initialize the SerpAPI class.
        
        Args:
            api_key (str): Your SerpAPI API key
            geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
            language (str): Language for the search. Defaults to "en"
            verbose (bool): Whether to print debug information
            print_func (Optional[callable]): Function to use for printing debug information
            **kwargs: Additional keyword arguments to pass to the SerpAPI class
        """
        super().__init__(**locals())

        # Initialize serpapi instance
        try:
            from serpapi import GoogleSearch
            self.search_client = GoogleSearch
        except ImportError:
            raise ImportError("serpapi library not installed. Please install it with 'pip install google-search-results'")

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> dict:
        """
        Search Google Trends using the SerpAPI library.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            
        Returns:
            dict: Raw search results
        """
        self.print_func(f"Sending SerpAPI search request:")
        self.print_func(f"  Search term: {search_term}")
        self.print_func(f"  Start date: {start_date if start_date else 'default'}")
        self.print_func(f"  End date: {end_date if end_date else 'default'}")
        self.print_func(f"  Language: {self.language}")
        
        try:
            # Prepare the parameters for the search
            params = {
                'api_key': self.api_key,
                'engine': 'google_trends',
                'q': search_term,
                'geo': self.geo,
                'hl': self.language
            }
            
            if start_date or end_date:
                params['date'] = make_time_range(start_date, end_date)
            
            # Add any additional parameters from kwargs
            params.update(self.kwargs)
            
            # Make the API call
            search = self.search_client(params)
            results = search.get_dict()
            
            self.print_func("  Search successful!")
            self.print_func(results)
            
            return results
                    
        except Exception as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise

def search_serpapi(
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
) -> dict:
    """
    Search Google Trends using the SerpAPI library.
    
    Args:
        search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
        start_date (Optional[Union[str, datetime]]): Start date for the search
        end_date (Optional[Union[str, datetime]]): End date for the search
        api_key (Optional[str]): The SerpAPI API key. If None, will try to get from environment variable SERPAPI_API_KEY
        geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
        language (str): Language for the search. Defaults to "en"
        tz (int): Timezone offset in minutes. Defaults to 0
        no_cache (bool): Whether to skip the cache. Defaults to False
        cat (Optional[int]): Category for the search. Defaults to None
        region (Optional[str]): Region for the search. Defaults to None
        verbose (bool): Whether to print debug information
        print_func (Optional[callable]): Function to use for printing debug information
        **kwargs: Additional keyword arguments to pass to the SerpAPI class
        
    Returns:
        dict: Raw search results
    """
    serp = SerpAPI(**locals())
    return serp.search(search_term, start_date, end_date) 