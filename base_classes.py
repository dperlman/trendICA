from typing import Union, List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

class API_Call:
    """
    Base class for API calls to various Google Trends APIs.
    This class defines the common interface and parameters used across different API implementations.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        proxy: Optional[str] = None,
        change_identity: bool = True,
        request_delay: int = 4,
        geo: str = "US",
        cat: int = 0,
        gprop: Optional[str] = None,
        language: str = "en",
        tz: int = 0,
        no_cache: bool = False,
        region: Optional[str] = None,
        verbose: bool = False,
        print_func: Optional[callable] = None,
        tor_control_password: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the API_Call class.
        
        Args:
            api_key (Optional[str]): API key for the service. Required for some APIs, optional for others
            proxy (Optional[str]): The proxy to use. If None, no proxy will be used. For Tor, use "127.0.0.1:9150"
            change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
            request_delay (int): Delay between requests in seconds
            geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
            cat (int): Category for the search. Defaults to 0 (all categories)
            gprop (Optional[str]): Google property to search. Defaults to None, which gives a web search. Options: "news", "images", "youtube", "froogle"
            language (str): Language for the search. Defaults to "en"
            tz (int): Timezone offset. Defaults to 0
            no_cache (bool): Whether to disable caching. Defaults to False
            region (Optional[str]): Region for the search
            verbose (bool): Whether to print debug information
            print_func (Optional[callable]): Function to use for printing debug information
            tor_control_password (Optional[str]): Password for Tor control port. Required if change_identity is True
            **kwargs: Additional keyword arguments specific to each API implementation
        """
        self.api_key = api_key
        self.proxy = proxy
        self.change_identity = change_identity
        self.request_delay = request_delay
        self.geo = geo
        self.cat = cat
        self.gprop = gprop
        self.language = language
        self.tz = tz
        self.no_cache = no_cache
        self.region = region
        self.verbose = verbose
        self.print_func = print_func if print_func is not None else print
        self.tor_control_password = tor_control_password
        self.kwargs = kwargs

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """
        Search Google Trends using the API.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            
        Returns:
            Union[pd.DataFrame, Dict[str, Any]]: The search results, either as a DataFrame or raw dictionary
        """
        raise NotImplementedError("Subclasses must implement search method") 