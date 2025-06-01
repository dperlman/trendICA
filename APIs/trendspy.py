import time
import requests
from datetime import datetime, timedelta
from typing import Union, List, Optional, Dict, Any
from utils import change_tor_identity, make_time_range
from .base_classes import API_Call
import pandas as pd

class TrendsPy(API_Call):
    def __init__(
        self,
        proxy: Optional[str] = None,
        change_identity: bool = True,
        request_delay: int = 4,
        tor_control_password: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the TrendsPy class.
        
        Args:
            proxy (Optional[str]): The proxy to use. If None, no proxy will be used. For Tor, use "127.0.0.1:9150"
            change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
            request_delay (int): Delay between requests in seconds
            tor_control_password (Optional[str]): Password for Tor control port. Required if change_identity is True
            **kwargs: Additional keyword arguments passed to API_Call
        """
        super().__init__(proxy=proxy, change_identity=change_identity, request_delay=request_delay, tor_control_password=tor_control_password, **kwargs)

        # Initialize trendspy instance
        try:
            import trendspy
            self.trends = trendspy.Trends(
                language=self.language,
                tzs=self.tz,  # Note: trendspy uses tzs instead of tz
                request_delay=request_delay,
                max_retries=1,
                proxy=self._get_proxy_config()
            )
        except ImportError:
            raise ImportError("trendspy library not installed. Please install it with 'pip install trendspy'")

    def _get_proxy_config(self) -> Optional[dict]:
        """Get proxy configuration dictionary if proxy is set."""
        if not self.proxy:
            return None
            
        proxy_config = {
            "http": f"socks5h://{self.proxy}",
            "https": f"socks5h://{self.proxy}"
        }
        
        # Test proxy connection
        try:
            test_response = requests.get('https://www.google.com', 
                                      proxies=proxy_config, 
                                      timeout=10)
            test_response.raise_for_status()
            return proxy_config
        except Exception as e:
            self.print_func(f"Proxy connection test failed: {str(e)}")
            self.print_func("Note: If using Tor Browser, make sure it's running and the SOCKS proxy is enabled")
            raise ValueError(f"Failed to connect to proxy {self.proxy}: {str(e)}")

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> 'TrendsPy':
        """
        Search Google Trends using the trendspy library.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            
        Returns:
            TrendsPy: Returns self for method chaining
        """
        self.print_func(f"Sending trendspy search request:")
        self.print_func(f"  Search term: {search_term}")
        self.print_func(f"  Start date: {start_date if start_date else 'default'}")
        self.print_func(f"  End date: {end_date if end_date else 'default'}")
        self.print_func(f"  Proxy: {self.proxy or 'None'}")
        self.print_func(f"  Change identity: {self.change_identity}")
        
        try:
            # Prepare the parameters for interest_over_time
            params = {
                'geo': self.geo,
                'cat': self.cat if self.cat is not None else 0,  # trendspy expects 0 as default
                'gprop': self.gprop if self.gprop is not None else ''  # trendspy expects empty string as default
            }
            if start_date or end_date:
                time_range = make_time_range(start_date, end_date)
                params['timeframe'] = time_range.ymd
                self.print_func(f"  Time range: {time_range.ymd}")
            else:
                self.print_func("  Time range: default")
            
            # If change_identity is True, change the Tor identity before the search
            if self.change_identity:
                self.print_func("  Changing Tor identity")
                change_tor_identity(self.tor_control_password, self.print_func)
            
            self.raw_data = self.trends.interest_over_time(search_term, return_raw=True, **params) # we want raw dicts because we will clean and standardize them all later
            
            # Check if there's an error in the results
            if isinstance(self.raw_data, dict) and "error" in self.raw_data:
                error_msg = self.raw_data["error"]
                self.print_func(f"  Search failed: {error_msg}")
                raise Exception(error_msg)
            
            self.print_func("  Search successful!")
            #self.print_func(self.raw_data)
            
            return self
                    
        except Exception as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise

    def standardize_data(self) -> 'TrendsPy':
        """
        Standardize the raw data into a common format.
        Transforms the interest_over_time data into a list of dictionaries with date and values.
        Note that this is experimental and may not work as expected.
        
        Returns:
            TrendsPy: Returns self for method chaining
        """
        if not hasattr(self, 'raw_data') or not self.raw_data:
            raise ValueError("No raw data available. Call search() first.")
            
        if not isinstance(self.raw_data, dict):
            raise ValueError("Raw data is not in the expected format")
            
        # Transform the data into the standardized format
        self.data = []
        for date, values in self.raw_data.items():
            standardized_entry = {
                'date': date,
                'values': [
                    {
                        'value': value,
                        'query': query
                    }
                    for query, value in values.items()
                ]
            }
            self.data.append(standardized_entry)
            
        return self

def search_trendspy(
    search_term: Union[str, List[str]],
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    proxy: Optional[str] = None,
    change_identity: bool = True,
    request_delay: int = 4,
    tor_control_password: Optional[str] = None,
    **kwargs
) -> Union[pd.DataFrame, Dict[str, Any]]:
    """
    Search Google Trends using the trendspy library.
    
    Args:
        search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
        start_date (Optional[Union[str, datetime]]): Start date for the search
        end_date (Optional[Union[str, datetime]]): End date for the search
        proxy (Optional[str]): The proxy to use. If None, no proxy will be used. For Tor, use "127.0.0.1:9150"
        change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
        request_delay (int): Delay between requests in seconds
        tor_control_password (Optional[str]): Password for Tor control port. Required if change_identity is True
        **kwargs: Additional keyword arguments passed to API_Call
        
    Returns:
        Union[pd.DataFrame, Dict[str, Any]]: Standardized search results
    """
    trends = TrendsPy(**locals())
    return trends.search(search_term, start_date, end_date).standardize_data().data
