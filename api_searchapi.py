import time
import requests
from datetime import datetime
from typing import Union, List, Optional
import pandas as pd
from utils import change_tor_identity

class SearchAPI:
    def __init__(
        self,
        api_key: str,
        proxy: Optional[str] = None,
        change_identity: bool = True,
        request_delay: int = 4,
        geo: str = "US",
        verbose: bool = False,
        print_func: Optional[callable] = None,
        tor_control_password: Optional[str] = None
    ):
        """
        Initialize the SearchAPI class.
        
        Args:
            api_key (str): Your SearchAPI API key
            proxy (Optional[str]): The proxy to use. If None, no proxy will be used. For Tor, use "127.0.0.1:9150"
            change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
            request_delay (int): Delay between requests in seconds
            geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
            verbose (bool): Whether to print debug information
            print_func (Optional[callable]): Function to use for printing debug information
            tor_control_password (Optional[str]): Password for Tor control port. Required if change_identity is True
        """
        self.api_key = api_key
        self.proxy = proxy
        self.change_identity = change_identity
        self.request_delay = request_delay
        self.geo = geo
        self.verbose = verbose
        self.print_func = print_func if print_func is not None else print
        self.tor_control_password = tor_control_password
        
        # Initialize searchapi instance
        try:
            import searchapi
            self.search_client = searchapi.SearchAPI(self.api_key)
        except ImportError:
            raise ImportError("searchapi library not installed. Please install it with 'pip install searchapi'")

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
    ) -> dict:
        """
        Search using SearchAPI.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up
            time_range (Optional[str]): Time range for the search
            
        Returns:
            dict: Raw search results
        """
        self.print_func(f"Sending SearchAPI search request:")
        self.print_func(f"  Search term: {search_term}")
        self.print_func(f"  Time range: {time_range if time_range else 'default'}")
        self.print_func(f"  Proxy: {self.proxy or 'None'}")
        self.print_func(f"  Change identity: {self.change_identity}")
        
        try:
            # Prepare the parameters for search
            params = {
                "q": search_term,
                "gl": self.geo.lower(),
                "num": 100  # Maximum results per page
            }
            
            if time_range:
                params['time_period'] = time_range
            
            # If change_identity is True, change the Tor identity before the search
            if self.change_identity:
                self.print_func("  Changing Tor identity")
                change_tor_identity(self.tor_control_password, self.print_func)
            
            results = self.search_client.search(params)
            self.print_func("  Search successful!")
            self.print_func(results)
            
            return results
                    
        except Exception as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise

def search_searchapi(
    search_term: Union[str, List[str]],
    api_key: str,
    time_range: Optional[str] = None,
    proxy: Optional[str] = None,
    change_identity: bool = True,
    request_delay: int = 4,
    geo: str = "US",
    verbose: bool = False,
    print_func: Optional[callable] = None,
    tor_control_password: Optional[str] = None
) -> dict:
    """
    Search using SearchAPI.
    
    Args:
        search_term (Union[str, List[str]]): The search term(s) to look up
        api_key (str): Your SearchAPI API key
        time_range (Optional[str]): Time range for the search
        proxy (Optional[str]): The proxy to use. If None, no proxy will be used. For Tor, use "127.0.0.1:9150"
        change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
        request_delay (int): Delay between requests in seconds
        geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
        verbose (bool): Whether to print debug information
        print_func (Optional[callable]): Function to use for printing debug information
        tor_control_password (Optional[str]): Password for Tor control port. Required if change_identity is True
        
    Returns:
        dict: Raw search results
    """
    search = SearchAPI(
        api_key=api_key,
        proxy=proxy,
        change_identity=change_identity,
        request_delay=request_delay,
        geo=geo,
        verbose=verbose,
        print_func=print_func,
        tor_control_password=tor_control_password
    )
    return search.search(search_term, time_range) 