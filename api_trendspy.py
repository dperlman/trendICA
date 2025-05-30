import time
import requests
from datetime import datetime
from typing import Union, List, Optional
import pandas as pd
from gtrend import get_index_granularity
from utils import change_tor_identity

class TrendsPy:
    def __init__(
        self,
        proxy: Optional[str] = None,
        change_identity: bool = True,
        request_delay: int = 4,
        geo: str = "US",
        cat: int = 0,
        verbose: bool = False,
        print_func: Optional[callable] = None,
        tor_password: Optional[str] = None
    ):
        """
        Initialize the TrendsPy class.
        
        Args:
            proxy (Optional[str]): The proxy to use. If None, no proxy will be used. For Tor, use "127.0.0.1:9150"
            change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
            request_delay (int): Delay between requests in seconds
            geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
            cat (int): Category for the search. Defaults to 0 (all categories)
            verbose (bool): Whether to print debug information
            print_func (Optional[callable]): Function to use for printing debug information
            tor_password (Optional[str]): Password for Tor control port. Required if change_identity is True
        """
        self.proxy = proxy
        self.change_identity = change_identity
        self.request_delay = request_delay
        self.geo = geo
        self.cat = cat
        self.verbose = verbose
        self.print_func = print_func if print_func is not None else print
        self.tor_password = tor_password
        
        # Initialize trendspy instance
        try:
            import trendspy
            self.trends = trendspy.Trends(
                proxy=self._get_proxy_config(),
                request_delay=request_delay,
                geo=geo,
                cat=cat
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
        time_range: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Search Google Trends using the trendspy library.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            time_range (Optional[str]): Time range for the search
            
        Returns:
            pd.DataFrame: A dataframe containing the timeseries data
        """
        self.print_func(f"Sending trendspy search request:")
        self.print_func(f"  Search term: {search_term}")
        self.print_func(f"  Time range: {time_range if time_range else 'default'}")
        self.print_func(f"  Proxy: {self.proxy or 'None'}")
        self.print_func(f"  Change identity: {self.change_identity}")
        
        try:
            # Prepare the parameters for interest_over_time
            params = {}
            if time_range:
                params['timeframe'] = time_range
            
            # Perform the search with the appropriate parameters
            max_retries = 1
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    # If change_identity is True, change the Tor identity before each attempt
                    if self.change_identity:
                        self.print_func(f"  Changing Tor identity for attempt {attempt + 1}")
                        change_tor_identity(self.tor_password, self.print_func)
                    
                    results = self.trends.interest_over_time(search_term, **params)
                    self.print_func("  Search successful!")
                    
                    return results
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.print_func(f"  Attempt {attempt + 1} failed: {str(e)}")
                        self.print_func(f"  Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        self.print_func(f"  All {max_retries} attempts failed")
                        raise
                    
        except Exception as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise 