from typing import Union, List, Optional, Dict, Any, Callable
from datetime import datetime
import pandas as pd
from gtrend_api_tools.utils import _print_if_verbose, load_config
from gtrend_api_tools.APIs.api_utils import standard_dict_to_df
from gtrend_api_tools.APIs.date_ranges import DateRange

class SearchSpec(DateRange):
    """
    A class that extends DateRange to include search terms.
    This class handles both date range and search terms for a single search operation.
    """
    def __init__(
        self,
        terms: Optional[Union[str, List[str]]] = None,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        granularity: str = 'D',
        verbose: bool = False
    ):
        """
        Initialize a SearchSpec instance.
        
        Args:
            terms (Optional[Union[str, List[str]]]): Search terms. If string, will be split on commas
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            granularity (str): The granularity of the date range. One of: 's' (seconds), 'm' (minutes), 'h' (hourly), 
                             'D' (daily), 'W' (weekly), 'M' (monthly), 'Q' (quarterly), 'Y' (yearly), 'X' (decade).
                             Defaults to 'D'.
            verbose (bool): Whether to print debug information
        """
        # Initialize DateRange first with dates
        super().__init__(start_date=start_date, end_date=end_date, granularity=granularity, verbose=verbose)
        
        # Handle terms
        if terms is not None:
            if isinstance(terms, str):
                self.terms = [term.strip() for term in terms.split(',')]
            else:
                self.terms = terms
            self.term_string = ','.join(self.terms)
        else:
            self.terms = []
            self.term_string = ''

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
        cat: Optional[int] = None,
        gprop: Optional[str] = None,
        language: str = "en",
        tz: int = 420,
        no_cache: bool = False,
        region: Optional[str] = None,
        verbose: bool = False,
        print_func: Optional[Callable] = None,
        tor_control_password: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        granularity: str = 'D',
        **kwargs
    ):
        """
        Initialize the API_Call class.
        
        Args:
            api_key (Optional[str]): API key for the service. Required for some APIs, optional for others
            proxy (Optional[str]): The proxy to use. If None, will use proxy from config.yaml if available
            change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
            request_delay (int): Delay between requests in seconds
            geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
            cat (Optional[int]): Category for the search. Defaults to None
            gprop (Optional[str]): Google property to search. Defaults to None
            language (str): Language for the search. Defaults to "en-US"
            tz (int): Timezone offset in minutes. Defaults to 420
            no_cache (bool): Whether to disable caching. Defaults to False
            region (Optional[str]): Region for the search. Defaults to None
            verbose (bool): Whether to print debug information
            print_func (Optional[Callable]): Function to use for printing debug information. If None, uses _print_if_verbose
            tor_control_password (Optional[str]): Password for Tor control port. Required if change_identity is True
            api_endpoint (Optional[str]): The API endpoint URL. Defaults to None
            granularity (str): The granularity of the date range. One of: 's' (seconds), 'm' (minutes), 'h' (hourly), 
                             'D' (daily), 'W' (weekly), 'M' (monthly), 'Q' (quarterly), 'Y' (yearly), 'X' (decade).
                             Defaults to 'D'.
            **kwargs: Additional keyword arguments specific to each API implementation
        """
        # Load config
        self.config = load_config()
        
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
        self.tor_control_password = tor_control_password
        self.api_endpoint = api_endpoint
        self.granularity = granularity
        self.kwargs = kwargs
        self._search_history = []
        self._raw_data_history = []
        self._data_history = []
        self._dataframe_history = []
        self._date_range = None

        # Create a closure that captures self.verbose
        def make_print_func(verbose: bool) -> callable:
            def print_with_verbose(message: str) -> None:
                _print_if_verbose(message, verbose)
            return print_with_verbose

        self.print_func = print_func if print_func is not None else make_print_func(self.verbose)

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> 'API_Call':
        """
        Search Google Trends using the API.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            
        Returns:
            API_Call: Returns self for method chaining. The raw data is stored in self.raw_data
        """
        # Create SearchSpec instance
        search_spec = SearchSpec(
            terms=search_term,
            start_date=start_date,
            end_date=end_date,
            granularity=self.granularity,
            verbose=self.verbose
        )
        

        # Set as current search_spec
        self.search_spec = search_spec

        return self

    def standardize_data(self) -> 'API_Call':
        """
        Standardize the raw data into a common format.
        For now, simply copies raw_data to data.
        
        Returns:
            API_Call: Returns self for method chaining
        """
        if not self._raw_data_history:
            raise ValueError("No raw data available. Call search() first.")
            
        self._data_history.append(self._raw_data_history[-1])
        return self

    def make_dataframe(self) -> 'API_Call':
        """
        Convert the standardized data to a pandas DataFrame.
        Uses standard_dict_to_df to create a DataFrame with a PeriodIndex.
        
        Returns:
            API_Call: Returns self for method chaining
        """
        if not self._data_history:
            raise ValueError("No standardized data available. Call standardize_data() first.")
            
        self._dataframe_history.append(standard_dict_to_df(self._data_history[-1]))
        return self

    @property
    def raw_data(self) -> Any:
        """
        Get the raw data from the API response.
        
        Returns:
            Any: The raw API response data
            
        Raises:
            ValueError: If no raw data is available
        """
        if not self._raw_data_history:
            raise ValueError("No raw data available. Call search() first.")
        return self._raw_data_history[-1]

    @raw_data.setter
    def raw_data(self, value: Any) -> None:
        """
        Set the raw data and append it to the history.
        
        Args:
            value (Any): The raw data to set
        """
        self._raw_data_history.append(value)

    @property
    def data(self) -> Any:
        """
        Get the standardized data.
        
        Returns:
            Any: The standardized data
            
        Raises:
            ValueError: If no standardized data is available
        """
        if not self._data_history:
            raise ValueError("No standardized data available. Call standardize_data() first.")
        return self._data_history[-1]

    @data.setter
    def data(self, value: Any) -> None:
        """
        Set the standardized data and append it to the history.
        
        Args:
            value (Any): The standardized data to set
        """
        self._data_history.append(value)

    @property
    def dataframe(self) -> pd.DataFrame:
        """
        Get the pandas DataFrame.
        
        Returns:
            pd.DataFrame: The pandas DataFrame
            
        Raises:
            ValueError: If no DataFrame is available
        """
        if not self._dataframe_history:
            raise ValueError("No DataFrame available. Call make_dataframe() first.")
        return self._dataframe_history[-1]

    @dataframe.setter
    def dataframe(self, value: pd.DataFrame) -> None:
        """
        Set the DataFrame and append it to the history.
        
        Args:
            value (pd.DataFrame): The DataFrame to set
        """
        self._dataframe_history.append(value)

    @property
    def raw_data_history(self) -> List[Any]:
        """
        Get the history of raw data.
        
        Returns:
            List[Any]: List of all raw data entries
        """
        return self._raw_data_history

    @property
    def data_history(self) -> List[Any]:
        """
        Get the history of standardized data.
        
        Returns:
            List[Any]: List of all standardized data entries
        """
        return self._data_history

    @property
    def dataframe_history(self) -> List[pd.DataFrame]:
        """
        Get the history of dataframes.
        
        Returns:
            List[pd.DataFrame]: List of all dataframe entries
        """
        return self._dataframe_history

    @property
    def search_history(self) -> List[Any]:
        """
        Get the search history.
        
        Returns:
            List[Any]: List of search terms used in previous searches
        """
        return self._search_history

    @search_history.setter
    def search_history(self, value: Any) -> None:
        """
        Add a search term to the search history.
        
        Args:
            value (Any): Search term to add to history
        """
        self._search_history.append(value)

    @property
    def search_spec(self) -> SearchSpec:
        """
        Get the current search specification.
        
        Returns:
            SearchSpec: The current search specification including terms and dates
            
        Raises:
            ValueError: If no search specification is available
        """
        if not self._search_history:
            raise ValueError("No search specification available. Call search() first.")
        return self._search_history[-1]

    @search_spec.setter
    def search_spec(self, spec: SearchSpec) -> None:
        """
        Set the current search specification and append it to the history.
        
        Args:
            spec (SearchSpec): Search specification to set
        """
        self._search_history.append(spec) 