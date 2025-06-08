import unicodedata
from typing import Dict, Any, Optional, List, Union, Tuple, Callable
from datetime import datetime, timedelta
import time
import pandas as pd
import math
import numpy as np
from scipy.optimize import minimize_scalar
from dateutil.parser import parse
import traceback

from utils import (
    load_config,
    get_index_granularity,
    _custom_mode,
    _print_if_verbose,
    calculate_search_granularity
)

# Import API_Call type for type hints
from APIs.base_classes import API_Call

class Trends:
    def __init__(
        self,
        api_keys: Optional[Dict[str, str]] = None,
        no_cache: bool = False,
        proxy: Optional[str] = None,
        change_identity: bool = True,
        request_delay: int = 4,
        geo: str = "US",
        cat: int = 0,
        tz: int = 420,
        region: Optional[str] = None,
        language: str = "en",
        dry_run: bool = False,
        verbose: bool = False,
        api: Optional[str] = None
    ) -> None:
        """
        Initialize the Trends class with configuration parameters.
        
        Args:
            api_keys (Optional[Dict[str, str]]): Dictionary of API keys, e.g. {'serpapi': 'key1', 'serpwow': 'key2'}
            no_cache (bool): Whether to skip cached results (only used with SerpAPI)
            proxy (Optional[str]): The proxy to use. If None, will use proxy from config.yaml if available
            change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
            request_delay (int): Delay between requests in seconds
            geo (str): Geographic location for the search (e.g. "US"). Defaults to "US"
            cat (int): Category for the search. Defaults to 0 (all categories)
            tz (int): Timezone offset in minutes from UTC. Defaults to 420 (US Pacific Time)
            region (Optional[str]): Region code for the search (e.g. "US-CA" for California). Defaults to None
            language (str): Language code for the search (e.g. "en" for English). Defaults to "en"
            dry_run (bool): If True, no actual API calls will be made. Instead, returns zero-filled dataframes
                           and prints what the API call would have been. Defaults to False.
            verbose (bool): If True, prints detailed information about the search process. Defaults to False.
            api (Optional[str]): Which API mode to use. Must match one of the modes defined in config.yaml:
                               - "trendspy": Use trendspy only
                               - "serpapi": Use SerpAPI only
                               - "serpwow": Use SerpWow only
                               - "searchapi": Use SearchAPI only
                               - "smart_tpy": Use trendspy, then fall back to paid APIs in order
                               - "smart_pyt": Use pytrends, then fall back to paid APIs (not implemented)
                               - "smart_sel": Use selenium, then fall back to paid APIs
                               - "smart_pay": Use paid APIs only in order
                               If None, defaults to "trendspy" mode.
        
        Raises:
            ValueError: If the specified API mode is not found in config.yaml
        """
        # Load config if it exists
        self.config = load_config()
        
        # Get API keys from config
        self.api_keys = self.config.get('api_keys', {})
        
        # Update API keys with provided values
        if api_keys:
            for api_name, key in api_keys.items():
                if key:  # Only update if a key was provided
                    self.api_keys[api_name] = key
        
        # Set API mode based on api argument
        if api:
            # Find the matching API mode in config
            api_modes = self.config.get('api_modes', [])
            matching_mode = next((mode for mode in api_modes if mode['name'] == api), None)
            if matching_mode:
                self.api_mode = matching_mode
            else:
                raise ValueError(f"Invalid API mode: {api}. Must be one of: {[mode['name'] for mode in api_modes]}")
        else:
            # Default to trendspy mode if no API specified
            self.api_mode = next((mode for mode in self.config.get('api_modes', []) if mode['name'] == 'trendspy'), None)
            if not self.api_mode:
                raise ValueError("No default API mode 'trendspy' found in config")
        
        # Set other parameters
        self.no_cache = no_cache
        self.proxy = proxy
        self.change_identity = change_identity
        self.request_delay = request_delay
        self.geo = geo
        self.cat = cat
        self.tz = tz
        self.region = region
        self.language = language
        self.dry_run = dry_run
        self.verbose = verbose
        self.api = api
        
        # Load Tor settings from config
        tor_config = self.config.get('tor', {})
        self.tor_control_password = tor_config.get('control_password')
        
        # Set proxy - use provided value or load from config
        if proxy is None and tor_config.get('proxy_port'):
            self.proxy = f"127.0.0.1:{tor_config['proxy_port']}"
        else:
            self.proxy = proxy
        
        # Initialize search logs
        self.main_log = []
        self.error_log = []
        self.warning_log = []
        self.rate_limit_log = []
        
        # Initialize API instances dictionary
        self.api_instances = {}

        # Set up wrapper methods for utility functions
        def _calculate_search_granularity_wrapper(
            start_date: Union[str, datetime],
            end_date: Union[str, datetime],
            verbose: Optional[bool] = None
        ) -> Dict[str, Union[str, pd.DatetimeIndex, pd.PeriodIndex]]:
            """Wrapper for calculate_search_granularity that includes config."""
            return calculate_search_granularity(
                start_date=start_date,
                end_date=end_date,
                config=self.config,
                verbose=verbose if verbose is not None else self.verbose
            )

        def _get_index_granularity_wrapper(index: pd.DatetimeIndex) -> str:
            """Wrapper for get_index_granularity."""
            return get_index_granularity(index)

        # Bind the wrapper methods to the instance
        self._calculate_search_granularity = _calculate_search_granularity_wrapper
        self._get_index_granularity = _get_index_granularity_wrapper

    def search(
        self,
        search_term: str,
        start_date: Union[str, datetime],
        end_date: Optional[Union[str, datetime]] = None,
        duration_days: Optional[int] = 270,
        granularity: str = "D",
        stagger: int = 0,
        trim: bool = True,
        scale: bool = True,
        combine: str = "median",
        final_scale: bool = True,
        round: int = 2,
        method: str = "MAD",
        raw_groups: bool = False
    ) -> 'Trends':
        """
        Search Google Trends for a given query.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_date (Union[str, datetime]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            duration_days (Optional[int]): Number of days to search from start_date if end_date not provided
            granularity (str): Time granularity for results. One of:
                - "D": Daily
                - "h": Hourly
                - "MS": Month start
                Defaults to "D"
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            trim (bool): Whether to drop rows with NA values because of the staggering. Defaults to True.
            scale (bool): Whether to scale overlapping intervals. Defaults to True.
            combine (str): How to combine multiple columns. Options are "mean", "median", or "mode". Defaults to "median".
            final_scale (bool): Whether to scale the final result so maximum value is 100. Defaults to True.
            round (int): Number of decimal places to round values to. Defaults to 2.
            method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
            raw_groups (bool): If True, returns the raw stagger groups without concatenating. Defaults to False.
            
        Returns:
            Trends: Returns self for method chaining
        """
        # Validate combine parameter
        if combine not in ["none", "mean", "median", "mode"]:
            raise ValueError(f"Invalid combine method: {combine}. Must be one of: none, mean, median, mode")
            
        # Parse dates
        start_dt = parse(start_date) if isinstance(start_date, str) else start_date
        end_dt = parse(end_date) if isinstance(end_date, str) and end_date else None
        
        prefix = "[DRY RUN] " if self.dry_run else ""
        message = (
            f"{prefix}Preparing to perform search with:\n"
            f"  Search term: {search_term}\n"
            f"  Start date: {start_dt}\n"
            f"  End date: {end_dt if end_dt else 'None (using duration_days=' + str(duration_days) + ')'}\n"
            f"  Granularity: {granularity}\n"
            f"  Stagger: {stagger}\n"
            f"  Scale: {scale}\n"
            f"  Combine: {combine}\n"
            f"  Final scale: {final_scale}\n"
            f"  Round: {round}\n"
            f"  Method: {method}\n"
            f"  Geo: {self.geo}\n"
            f"  Category: {self.cat}"
        )
        message += f"\n  Using API mode: {self.api_mode['name']}"
        self._print(message)
        
        # If no end_date provided, calculate it from duration_days
        if end_dt is None:
            if granularity == "D":
                end_dt = start_dt + timedelta(days=duration_days)
            elif granularity == "h":
                end_dt = start_dt + timedelta(hours=duration_days * 24)
            else:  # MS
                # For month start, we'll use duration_days as approximate months
                end_dt = start_dt
                for _ in range(duration_days):
                    # Get the last day of the current month
                    last_day = (end_dt.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                    # Move to the first day of next month
                    end_dt = (last_day + timedelta(days=1)).replace(day=1)
        
        # Calculate appropriate granularity based on date range
        granularity_info = self._calculate_search_granularity(
            start_date=start_dt,
            end_date=end_dt
        )
        granularity = granularity_info['granularity']
        
        # Choose appropriate search function based on parameters
        if stagger > 0:
            # Use staggered search for any granularity when stagger is requested
            results = self._search_staggered(
                search_term=search_term,
                start_dt=start_dt,
                end_dt=end_dt,
                granularity=granularity,
                search_unit_length=duration_days,
                stagger=stagger,
                scale=scale,
                method=method
            )
        else:
            # For non-staggered searches, use appropriate method based on granularity
            if granularity == "D":
                results = self._search_by_day(
                    search_term=search_term,
                    start_date=start_dt,
                    end_date=end_dt
                )
            elif granularity == "h":
                results = self._search_by_hour(
                    search_term=search_term,
                    start_date=start_dt,
                    end_date=end_dt
                )
            else:  # MS
                results = self._search_by_day(
                    search_term=search_term,
                    start_date=start_dt,
                    end_date=end_dt
                )

        # Print search log summary
        prefix = "[DRY RUN] " if self.dry_run else ""
        message = (
            f"\n{prefix}Search Summary:\n"
            f"Total searches performed: {len(self.main_log)}\n"
            f"API mode: {self.api_mode['name']}\n"
            "\nSearch details:"
        )
        for i, log in enumerate(self.main_log, 1):
            error_str = f" [ERROR: {log['error']}]" if 'error' in log else ""
            warning_str = f" [WARNING: {log['warning']}]" if 'warning' in log else ""
            message += f"\nSearch {i}: {log['search_term']} | {log['start_date']} to {log['end_date']} | {log['api']} | {log['granularity']}{error_str}{warning_str}"
        self._print(message)
        
        return self

    def search_by_day(
        self,
        search_term: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        stagger: int = 0,
        trim: bool = True,
        scale: bool = True,
        combine: str = "median",
        final_scale: bool = True,
        round: int = 2,
        method: str = "MAD",
        raw_groups: bool = False
    ) -> 'Trends':
        """
        Search Google Trends for a given query with daily granularity.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_date (Union[str, datetime]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            trim (bool): Whether to drop rows with NA values because of the staggering. Defaults to True.
            scale (bool): Whether to scale overlapping intervals. Defaults to True.
            combine (str): How to combine multiple columns. Options are "mean", "median", or "mode". Defaults to "median".
            final_scale (bool): Whether to scale the final result so maximum value is 100. Defaults to True.
            round (int): Number of decimal places to round values to. Defaults to 2.
            method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
            raw_groups (bool): If True, returns the raw stagger groups without concatenating. Defaults to False.
            
        Returns:
            Trends: Returns self for method chaining
        """
        self._search_by_day(
            search_term=search_term,
            start_date=start_date,
            end_date=end_date,
            stagger=stagger,
            trim=trim,
            scale=scale,
            combine=combine,
            final_scale=final_scale,
            round=round,
            method=method,
            raw_groups=raw_groups
        )
        return self

    def _search_by_day(
        self,
        search_term: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        stagger: int = 0,
        trim: bool = True,
        scale: bool = True,
        combine: str = "median",
        final_scale: bool = True,
        round: int = 2,
        method: str = "MAD",
        raw_groups: bool = False
    ) -> Union[pd.DataFrame, List[List[pd.DataFrame]], Dict[str, str], List[datetime]]:
        """
        Internal method to search Google Trends with daily granularity over multiple 270-day intervals.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_date (Union[str, datetime]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            trim (bool): Whether to drop rows with NA values because of the staggering. Defaults to True.
            scale (bool): Whether to scale overlapping intervals. Defaults to True.
            combine (str): How to combine multiple columns. Options are "mean", "median", or "mode". Defaults to "median".
            final_scale (bool): Whether to scale the final result so maximum value is 100. Defaults to True.
            round (int): Number of decimal places to round values to. Defaults to 2.
            method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
            raw_groups (bool): If True, returns the raw stagger groups without concatenating. Defaults to False.
            
        Returns:
            Union[pd.DataFrame, List[List[pd.DataFrame]], Dict[str, str], List[datetime]]: 
                - If raw_groups is True: Returns the raw stagger groups
                - If dry_run is True: Returns a processed DataFrame with dummy data (zero values)
                - If an error occurs: Returns a dictionary with error information
                - Otherwise: Returns a processed DataFrame with the combined and scaled results
                
        Raises:
            ValueError: If combine is not one of "none", "mean", "median", or "mode"
        """
        # Validate combine parameter
        if combine not in ["none", "mean", "median", "mode"]:
            raise ValueError(f"Invalid combine method: {combine}. Must be one of: none, mean, median, mode")
            
        prefix = "[DRY RUN] " if self.dry_run else ""
        message = (
            f"{prefix}Preparing to perform search with:\n"
            f"  Search term: {search_term}\n"
            f"  Start date: {start_date}\n"
            f"  End date: {end_date}\n"
            f"  Stagger: {stagger}\n"
            f"  Scale: {scale}\n"
            f"  Method: {method}\n"
            f"  Combine: {combine}\n"
            f"  Final scale: {final_scale}\n"
            f"  Round: {round}\n"
            f"  API: {self.api if hasattr(self, 'api') and self.api else 'auto-select'}"
        )
        self._print(message)
        
        # Convert dates to datetime if they're strings
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_dt = start_date
            
        if isinstance(end_date, str):
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = end_date
        
        # Calculate total days
        total_days = (end_dt - start_dt).days + 1
        
        # If total days is less than or equal to 270, use a single search
        if total_days <= 270:
            result = self._search_by_day_270(
                search_term=search_term,
                start_date=start_dt
            )
            return result
        
        # For ranges longer than 270 days, use staggered searches
        stagger_groups = self._search_staggered(
            search_term=search_term,
            start_dt=start_dt,
            end_dt=end_dt,
            granularity="D",
            stagger=stagger,
            scale=scale,
            method=method
        )
        
        if raw_groups or combine == "none":
            return stagger_groups

        # Combine results within each stagger group
        final_dfs = []
        for i, group in enumerate(stagger_groups):
            if group:
                combined = pd.concat(group, axis=0)
                combined.columns = [f"{col}_{i+1}" for col in combined.columns]
                final_dfs.append(combined)
        
        # Combine all stagger groups into final dataframe
        if final_dfs:
            result_df = pd.concat(final_dfs, axis=1)
            if trim:
                # Drop rows where all values are NA
                result_df = result_df.dropna(how='any')
                
            # Combine columns using the specified method
            if combine == "mean":
                result_df = pd.DataFrame(result_df.mean(axis=1), columns=[search_term.replace(" ", "_")])
            elif combine == "median":
                result_df = pd.DataFrame(result_df.median(axis=1), columns=[search_term.replace(" ", "_")])
            elif combine == "mode":
                result_df = pd.DataFrame(self._custom_mode(result_df, axis=1),
                                       index=result_df.index,
                                       columns=[search_term.replace(" ", "_")])
            
            if final_scale:
                # Scale the result so maximum value is 100
                max_val = result_df.max().max()
                if max_val > 0:  # Avoid division by zero
                    result_df = result_df * (100 / max_val)
                
            # Round all values to specified number of decimal places
            if round is not None:
                result_df = result_df.round(round)

            # Print search log summary
            message = (
                f"\n{prefix}Search Summary:\n"
                f"Total searches performed: {len(self.main_log)}\n"
                f"API used: {self.last_api_used}\n"
                "\nSearch details:"
            )
            for i, log in enumerate(self.main_log, 1):
                error_str = f" [ERROR: {log['error']}]" if 'error' in log else ""
                warning_str = f" [WARNING: {log['warning']}]" if 'warning' in log else ""
                message += f"\nSearch {i}: {log['search_term']} | {log['start_date']} to {log['end_date']} | {log['api']} | {log['granularity']}{error_str}{warning_str}"
            self._print(message)

            return result_df
        return pd.DataFrame()

    def _search_by_day_270(
        self,
        search_term: str,
        start_date: Union[str, datetime]
    ) -> pd.DataFrame:
        """
        Perform a Google Trends search with daily granularity over a 270-day period.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_date (Union[str, datetime]): Start date for the search
            
        Returns:
            pd.DataFrame: A dataframe containing the timeseries data with daily granularity
            
        Note:
            This method will validate that the returned data has daily granularity.
            If a different granularity is detected, a warning will be logged and printed.
        """
        # Convert start_date to datetime if it's a string, otherwise use as is
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_dt = start_date
        
        # Calculate end_date (270 days total, that's why we add 269 days, because it includes start and end)
        end_dt = start_dt + timedelta(days=269)
        
        if self.dry_run:
            # Create a date range with daily frequency
            date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
            result = pd.DataFrame(0, index=date_range, columns=[search_term.replace(" ", "_")])
            return result
        
        # Perform the search using the chosen API
        self.api_instance = self._search_with_chosen_api(
            search_term=search_term,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Get the raw data from the API instance
        results = self.api_instance.standardize_data().make_dataframe().dataframe
        
        # If results is a DataFrame, validate its granularity
        if isinstance(results, pd.DataFrame):
            actual_granularity = self._get_index_granularity(results.index)
            if actual_granularity != 'D':
                warning_msg = f"Expected daily granularity but got {actual_granularity}"
                # Print warning immediately with detailed information
                self._print(f"\nWARNING: {warning_msg}")
                self._print(f"  Search term: {search_term}")
                self._print(f"  Start date: {start_dt.strftime('%Y-%m-%d')}")
                self._print(f"  End date: {end_dt.strftime('%Y-%m-%d')}")
                self._print(f"  API mode: {self.api_mode['name']}")
                # Log the warning
                self._log(
                    search_term=search_term,
                    start_date=start_dt,
                    end_date=end_dt,
                    api=self.api_mode['name'],
                    granularity=actual_granularity,
                    warning=warning_msg
                )
        
        return results

    def _search_by_hour(
        self,
        search_term: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        stagger: int = 0,
        trim: bool = True,
        scale: bool = True,
        combine: str = "median",
        final_scale: bool = True,
        round: int = 2,
        method: str = "MAD",
        raw_groups: bool = False
    ) -> pd.DataFrame:
        """
        Perform a Google Trends search with hourly granularity.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_date (Union[str, datetime]): Start date for the search
            end_date (Union[str, datetime]): End date for the search
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            trim (bool): Whether to drop rows with NA values because of the staggering. Defaults to True.
            scale (bool): Whether to scale overlapping intervals. Defaults to True.
            combine (str): How to combine multiple columns. Options are "mean", "median", or "mode". Defaults to "median".
            final_scale (bool): Whether to scale the final result so maximum value is 100. Defaults to True.
            round (int): Number of decimal places to round values to. Defaults to 2.
            method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
            raw_groups (bool): If True, returns the raw stagger groups without concatenating. Defaults to False.
            
        Returns:
            pd.DataFrame: A dataframe containing the timeseries data with hourly granularity
        """
        # Parse the time range
        start_dt = parse(start_date) if isinstance(start_date, str) else start_date
        end_dt = parse(end_date) if isinstance(end_date, str) else end_date

        if self.dry_run:
            # Create a date range with hourly frequency
            date_range = pd.date_range(start=start_dt, end=end_dt, freq='h')
            result = pd.DataFrame(0, index=date_range, columns=[search_term.replace(" ", "_")])
            return result

        # Convert to ISO format strings
        start_date = start_dt.strftime("%Y-%m-%dT%H")
        end_date = end_dt.strftime("%Y-%m-%dT%H")
        
        # Perform the search using the chosen API
        self.api_instance = self._search_with_chosen_api(
            search_term=search_term,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Get the raw data from the API instance
        results = self.api_instance.standardize_data().make_dataframe().dataframe
        
        # Apply final scaling if requested
        if final_scale and not self.dry_run:
            max_val = results.max().max()
            if max_val > 0:
                results = results * (100 / max_val)
        
        # Round values if requested
        if round is not None:
            results = results.round(round)
            
        return results

    def _calculate_stagger(
        self,
        start_dt: datetime,
        end_dt: datetime,
        granularity: str = "D",
        search_unit_length: int = 270,
        stagger: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Calculate the stagger intervals for a given date range.
        
        Args:
            start_dt (datetime): Start date for the search
            end_dt (datetime): End date for the search
            granularity (str): Time granularity for results. One of:
                - "D": Daily
                - "h": Hourly
                - "MS": Month start
                Defaults to "D"
            search_unit_length (int): Number of time units in each search. Defaults to 270 (days)
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing search information:
                - start_date: datetime - The start date for this search
                - group_idx: int - Which stagger group this search belongs to (0 to stagger)
                - interval_idx: int - Which interval within the group this is
                
        Raises:
            ValueError: If granularity is not one of "D", "h", or "MS"
        """
        # Validate granularity
        if granularity not in ["D", "h", "MS"]:
            raise ValueError("granularity must be one of: 'D' (daily), 'h' (hourly), or 'MS' (month start)")
            
        # Calculate total time units between start and end
        if granularity == "D":
            total_units = (end_dt - start_dt).days
            time_unit = timedelta(days=1)
        elif granularity == "h":
            total_units = int((end_dt - start_dt).total_seconds() / 3600)
            time_unit = timedelta(hours=1)
        else:  # MS
            # Calculate months between dates
            total_units = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
            # For month start, we'll use a month as the time unit
            time_unit = timedelta(days=30)  # Approximate, will be adjusted in the loop
            
        # Calculate number of intervals needed
        base_intervals = math.ceil(total_units / search_unit_length)
        
        # Calculate overlap factor
        if stagger == 0:
            overlap_factor = 0
        else:
            overlap_factor = 1 / (stagger + 1)
        
        # Calculate stagger units
        stagger_units = math.floor(search_unit_length * overlap_factor)
        
        # Create list to store search information
        searches = []
        
        # For each stagger group
        for s in range(stagger + 1):
            # Calculate current start based on stagger units
            if granularity == "MS":
                # For month start, we need to handle month boundaries
                current_start = start_dt.replace(day=1)  # Start of month
                # Move back by stagger months
                for _ in range((stagger - s) * stagger_units):
                    current_start = (current_start.replace(day=1) - timedelta(days=1)).replace(day=1)
            else:
                current_start = start_dt - (time_unit * (stagger - s) * stagger_units)
            
            # Calculate how many intervals we need for this group
            # For the last group, we need base_intervals
            # For other groups, we need base_intervals + 1
            intervals_needed = base_intervals if s == stagger else base_intervals + 1
            
            # Add each interval to the list
            for i in range(intervals_needed):
                searches.append({
                    'start_date': current_start,
                    'group_idx': s,
                    'interval_idx': i
                })
                if granularity == "MS":
                    # Move forward by search_unit_length months
                    for _ in range(search_unit_length):
                        # Get the last day of the current month
                        last_day = (current_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                        # Move to the first day of next month
                        current_start = (last_day + timedelta(days=1)).replace(day=1)
                else:
                    current_start = current_start + (time_unit * search_unit_length)
        
        return searches

    def _search_staggered(
        self,
        search_term: str,
        start_dt: datetime,
        end_dt: datetime,
        granularity: str = "D",
        search_unit_length: int = 270,
        stagger: int = 0,
        scale: bool = True,
        method: str = "MAD"
    ) -> List[List[pd.DataFrame]]:
        """
        Perform staggered searches over multiple intervals.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_dt (datetime): Start date for the search
            end_dt (datetime): End date for the search
            granularity (str): Time granularity for results. One of:
                - "D": Daily
                - "h": Hourly
                - "MS": Month start
                Defaults to "D"
            search_unit_length (int): Number of time units in each search. Defaults to 270 (days)
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            scale (bool): Whether to scale overlapping intervals. Defaults to True.
            method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
            
        Returns:
            List[List[pd.DataFrame]]: List of stagger groups, each containing a list of dataframes.
            Each dataframe contains search_unit_length time units of data with specified granularity.
        """
        # Calculate all the searches we need to perform
        searches = self._calculate_stagger(
            start_dt=start_dt,
            end_dt=end_dt,
            granularity=granularity,
            search_unit_length=search_unit_length,
            stagger=stagger
        )
        
        # Create list to store results for each stagger group
        stagger_groups = [[] for _ in range(stagger + 1)]
        
        # Initialize search counter
        search_count = 0
        
        # Perform each search and store results in appropriate group
        for search_info in searches:
            search_count += 1
            if granularity == "D":
                # Calculate end date based on search_unit_length
                end_date = search_info['start_date'] + timedelta(days=search_unit_length)
                result = self._search_by_day_270(
                    search_term=search_term,
                    start_date=search_info['start_date'] # search_by_day_270 takes care of the end date
                )
            elif granularity == "h":
                result = self._search_by_hour(
                    search_term=search_term,
                    start_date=search_info['start_date'],
                    end_date=search_info['start_date'] + timedelta(hours=search_unit_length)
                )
            else:  # MS
                # For month start, calculate end date by moving forward search_unit_length months
                end_date = search_info['start_date']
                for _ in range(search_unit_length):
                    # Get the last day of the current month
                    last_day = (end_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                    # Move to the first day of next month
                    end_date = (last_day + timedelta(days=1)).replace(day=1)
                result = self._search_by_day(
                    search_term=search_term,
                    start_date=search_info['start_date'],
                    end_date=end_date
                )
            stagger_groups[search_info['group_idx']].append(result)
        
        # if self.dry_run:
        #     self._print(f"[DRY RUN] Would perform {search_count} searches:")
        #     for s, group in enumerate(stagger_groups):
        #         for i, df in enumerate(group):
        #             if granularity == "h":
        #                 date_format = '%Y-%m-%d %H:%M'
        #             else:
        #                 date_format = '%Y-%m-%d'
        #             start_date = df.index[0].strftime(date_format)
        #             end_date = df.index[-1].strftime(date_format)
        #             self._print(f"Group {s+1}, Interval {i+1}: {start_date} to {end_date}")
        
        if stagger > 0 and scale and not self.dry_run:
            stagger_groups = self._scale_stagger_groups(stagger_groups, method)
            
        return stagger_groups

    def _print(self, *args, **kwargs):
        """
        Print message only if verbose is True.
        
        Args:
            *args: Arguments to pass to print
            **kwargs: Keyword arguments to pass to print
        """
        _print_if_verbose(*args, **kwargs, verbose=self.verbose)

    def _log(
        self,
        search_term: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        api: str,
        granularity: str,
        error: Optional[str] = None,
        warning: Optional[str] = None
    ) -> None:
        """
        Log a search attempt with its details and any errors.
        
        Args:
            search_term (str): The search term used
            start_date (Union[str, datetime]): The start date of the search
            end_date (Union[str, datetime]): The end date of the search
            api (str): The API used for the search
            granularity (str): The granularity of the data ('h' for hour, 'D' for day, 'W' for week, or 'ME' for month end)
            error (Optional[str]): Any error message if the search failed
            warning (Optional[str]): Any warning message about the search results
        """
        formatted_utc_gmtime = time.strftime("%Y-%m-%dT%H-%MUTC", time.gmtime())
        log_entry = {
            "search_term": search_term,
            "start_date": start_date,
            "end_date": end_date,
            "search_time": formatted_utc_gmtime,
            "api": api,
            "granularity": granularity
        }
        if error:
            log_entry["error"] = error
        if warning:
            log_entry["warning"] = warning
        self.main_log.append(log_entry)

    def _scale_stagger_groups(
        self,
        stagger_groups: List[List[pd.DataFrame]],
        method: str = "MAD",
        reference: Union[str, int] = "first"
    ) -> List[List[pd.DataFrame]]:
        """
        Scale overlapping intervals in stagger groups.
        
        Args:
            stagger_groups (List[List[pd.DataFrame]]): List of stagger groups, each containing a list of dataframes
            method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
            reference (Union[str, int]): Which group to use as reference. Options are:
                - "first": Use the first interval as reference
                - "last": Use the last interval as reference
                - "lowest_median": Use the interval with lowest median value as reference
                - "highest_median": Use the interval with highest median value as reference
                - int: Use the interval at this index as reference (0-based)
            
        Returns:
            List[List[pd.DataFrame]]: Scaled stagger groups
            
        Raises:
            ValueError: If reference is invalid or if dataframes have incorrect structure
        """
        # Validate input structure
        if not stagger_groups or not all(isinstance(group, list) for group in stagger_groups):
            raise ValueError("stagger_groups must be a non-empty list of lists")
        
        # Get the maximum number of intervals across all groups
        max_intervals = max(len(group) for group in stagger_groups)
        
        # Validate that all dataframes have exactly one column
        for group in stagger_groups:
            for df in group:
                if not isinstance(df, pd.DataFrame) or len(df.columns) != 1:
                    raise ValueError("Each dataframe must have exactly one column")
        
        # Create a list of (group_idx, interval_idx) pairs in the correct scaling order
        scaling_order = []
        flat_groups = []
        for interval_idx in range(max_intervals):
            for group_idx in range(len(stagger_groups)):
                if interval_idx < len(stagger_groups[group_idx]):
                    scaling_order.append((group_idx, interval_idx))
                    flat_groups.append(stagger_groups[group_idx][interval_idx])
        
        # Create a copy of the flat list to work with
        working_groups = [df.copy() for df in flat_groups]
        
        # Determine the reference index
        if isinstance(reference, int):
            if reference < 0 or reference >= len(working_groups):
                raise ValueError(f"Reference index {reference} is out of range [0, {len(working_groups)-1}]")
            ref_idx = reference
        elif reference == "first":
            ref_idx = 0
        elif reference == "last":
            ref_idx = len(working_groups) - 1
        elif reference in ["lowest_median", "highest_median"]:
            # Calculate median for each dataframe
            medians = [df.median().mean() for df in flat_groups]
            
            # Find index of dataframe with lowest or highest median
            if reference == "lowest_median":
                ref_idx = medians.index(min(medians))
            else:  # highest_median
                ref_idx = medians.index(max(medians))
        else:
            raise ValueError("reference must be one of: 'first', 'last', 'lowest_median', 'highest_median', or an integer")
        
        # Scale forward from reference
        for i in range(ref_idx + 1, len(working_groups)):
            ref_df = working_groups[i-1]
            current_df = working_groups[i]
            working_groups[i] = self._scale_series(ref_df, current_df, method=method)
        
        # Scale backward from reference
        for i in range(ref_idx - 1, -1, -1):
            ref_df = working_groups[i + 1]
            current_df = working_groups[i]
            working_groups[i] = self._scale_series(ref_df, current_df, method=method)
        
        # Reshape back into original structure
        result_groups = [[] for _ in range(len(stagger_groups))]
        for flat_idx, (group_idx, interval_idx) in enumerate(scaling_order):
            # Ensure the group has enough space
            while len(result_groups[group_idx]) <= interval_idx:
                result_groups[group_idx].append(None)
            result_groups[group_idx][interval_idx] = working_groups[flat_idx]
        
        return result_groups

    def _scale_series(self, series1: pd.Series, series2: pd.Series, method: str = "MAD") -> pd.Series:
        """
        Scale the second series to minimize either the sum of squared differences (SSD) or 
        median absolute difference (MAD) with the first series over their overlapping time periods.
        
        Args:
            series1 (pd.Series): First series with datetime index
            series2 (pd.Series): Second series with datetime index to be scaled
            method (str): Method to use for scaling. Either "SSD" or "MAD" (case insensitive).
                Defaults to "MAD".
            
        Returns:
            pd.Series: Scaled second series
            
        Raises:
            ValueError: If either series does not have a datetime index or if method is invalid
        """
        # Check if both series have datetime index
        if not isinstance(series1.index, pd.DatetimeIndex) or not isinstance(series2.index, pd.DatetimeIndex):
            raise ValueError("Both series must have datetime index")
        
        # Validate method
        method = method.upper()
        if method not in ["SSD", "MAD"]:
            raise ValueError("Method must be either 'SSD' or 'MAD'")
        
        # Find overlapping dates
        common_dates = series1.index.intersection(series2.index)
        
        # If no overlap, return original series2
        if len(common_dates) == 0:
            return series2
        
        # Get values for overlapping dates using loc
        x = series1.loc[common_dates].values
        y = series2.loc[common_dates].values
        
        if method == "SSD":
            # Calculate original sum of squared differences
            original_diff = np.sum((x - y) ** 2)
            self._print(f"Original sum of squared differences: {original_diff}")
            
            # Calculate scale factor that minimizes sum of squared differences
            # Using the formula: scale = sum(x*y) / sum(y*y)
            scale_factor = np.sum(x * y) / np.sum(y * y)
            
            # Apply scale factor to second series
            scaled_series2 = series2 * scale_factor
            
            # Calculate final sum of squared differences
            final_diff = np.sum((x - scaled_series2.loc[common_dates].values) ** 2)
            self._print(f"Final sum of squared differences: {final_diff}")
        else:  # MAD
            # Calculate original median absolute difference
            original_diff = np.median(np.abs(x - y))
            self._print(f"Original median absolute difference: {original_diff}")
            
            # Use iterative optimization to find scale factor that minimizes MAD
            def mad_objective(scale):
                return np.median(np.abs(x - y * scale))
            
            result = minimize_scalar(mad_objective)
            scale_factor = result.x
            
            # Apply scale factor to second series
            scaled_series2 = series2 * scale_factor
            
            # Calculate final median absolute difference
            final_diff = np.median(np.abs(x - scaled_series2.loc[common_dates].values))
            self._print(f"Final median absolute difference: {final_diff}")
        
        return scaled_series2

    def _search_with_chosen_api(
        self,
        search_term: Union[str, List[str]],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime]
    ) -> API_Call:
        """
        Search using the chosen API from the config file's api_order list.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Union[str, datetime]): Start date for the search
            end_date (Union[str, datetime]): End date for the search
            
        Returns:
            API_Call: The API instance that performed the search
            
        Raises:
            Exception: If all APIs in the order fail
        """
        from APIs import available_apis
        
        # Try each API in the configured order
        for api_name in self.api_mode['api_order']:
            self._print(f"Trying API: {api_name}")
            api_info = available_apis[api_name]
            
            # For paid APIs, check if we have the key
            if api_info['type'] == 'paid':
                if api_name not in self.api_keys or not self.api_keys[api_name]:
                    self._print(f"Skipping {api_name} - no API key available")
                    continue
            
            # Try to reuse existing API instance if available
            if api_name in self.api_instances:
                api_instance = self.api_instances[api_name]
            else:
                # Create new API instance with our config
                api_instance = api_info['class'](
                    api_key=self.api_keys.get(api_name),
                    proxy=self.proxy,
                    change_identity=self.change_identity,
                    request_delay=self.request_delay,
                    tor_control_password=self.tor_control_password,
                    verbose=self.verbose,
                    print_func=self._print
                )
                # Store the instance for potential reuse
                self.api_instances[api_name] = api_instance
                # Store the current api instance so downstream functions know which one it was
                self.api_instance = api_instance

            
            # Try to perform the search
            try:
                api_instance.search(
                    search_term=search_term,
                    start_date=start_date,
                    end_date=end_date
                )
                self.last_api_used = api_name
                self.last_api_instance = api_instance
                return api_instance
            except Exception as e:
                self._print(f"Error with {api_name}: {str(e)}")
                print(traceback.format_exc())
                continue
        
        raise Exception("All APIs in the configured order failed")

    def standardize_data(self) -> 'Trends':
        """
        Forward the standardize_data call to the API instance.
        
        Returns:
            Trends: Returns self for method chaining
        """
        if not hasattr(self, 'api_instance') or not self.api_instance:
            raise ValueError("No API instance available. Call search() first.")
            
        self.api_instance.standardize_data()
        return self

    def make_dataframe(self) -> 'Trends':
        """
        Forward the make_dataframe call to the API instance.
        
        Returns:
            Trends: Returns self for method chaining
        """
        if not hasattr(self, 'api_instance') or not self.api_instance:
            raise ValueError("No API instance available. Call search() first.")
            
        self.api_instance.make_dataframe()
        return self

    @property
    def data(self):
        """
        Forward the data property to the API instance.
        """
        if not hasattr(self, 'api_instance') or not self.api_instance:
            raise ValueError("No API instance available. Call search() first.")
            
        return self.api_instance.data

    @property
    def raw_data(self):
        """
        Forward the raw_data property to the API instance.
        """
        if not hasattr(self, 'api_instance') or not self.api_instance:
            raise ValueError("No API instance available. Call search() first.")
            
        return self.api_instance.raw_data

    @property
    def df(self):
        """
        Forward the dataframe property to the API instance.
        """
        if not hasattr(self, 'api_instance') or not self.api_instance:
            raise ValueError("No API instance available. Call search() first.")
            
        return self.api_instance.dataframe


# Example usage
if __name__ == "__main__":
    print("This is a library, not a script. It is used to do google trends searches easily.")
    