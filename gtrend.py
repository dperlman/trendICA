#! /opt/miniconda3/envs/trendspy/bin/python3

import unicodedata
from typing import Dict, Any, Optional, List, Union, Tuple, Callable
from datetime import datetime, timedelta
import time
import trendspy
import pandas as pd
import socket
import os
import sys
import re
import math
import numpy as np
from scipy.optimize import minimize_scalar
from scipy import stats
import requests
import json
from keys import SERPAPI_API_KEY, SERPWOW_API_KEY, SEARCHAPI_API_KEY

# Module-level variable to store the last caller
_last_caller = None

def _print_if_verbose(message: str, verbose: bool = False) -> None:
    """
    Print message only if verbose is True, prefixed with the caller's function name.
    If the caller is _print, uses the caller of _print instead.
    Only prints the caller name if it has changed from the last call.
    
    Args:
        message (str): The message to print
        verbose (bool): Whether to print the message
    """
    if verbose:
        import inspect
        global _last_caller
        
        # Get the caller's frame info
        caller = inspect.currentframe().f_back
        # Get the caller's function name
        caller_name = caller.f_code.co_name
        
        # If the caller is _print, get the caller of _print instead
        if caller_name == '_print':
            caller = caller.f_back
            caller_name = caller.f_code.co_name
        
        # Only print the caller name if it has changed
        if caller_name != _last_caller:
            print(f"\n[{caller_name}]")
            _last_caller = caller_name
            
        # Print the message
        print(message)


def _get_index_granularity(index: pd.DatetimeIndex, verbose: bool = False) -> str:
    """
    Determine the granularity of a pandas DateTimeIndex.
    
    Args:
        index (pd.DatetimeIndex): The DateTimeIndex to analyze
        verbose (bool): Whether to print debug information
        
    Returns:
        str: The granularity code ('H' for hour, 'D' for day, 'W' for week, 'M' for month)
    """
    # Handle empty DataFrame or non-DatetimeIndex
    if len(index) == 0 or not isinstance(index, pd.DatetimeIndex):
        return 'D'  # Default to daily granularity
        
    # First try to get the frequency directly
    if index.freq is not None:
        freq_str = str(index.freq)
        if 'H' in freq_str:
            return 'H'
        elif 'D' in freq_str:
            return 'D'
        elif 'W' in freq_str:
            return 'W'
        elif 'M' in freq_str:
            return 'M'
    
    # If no frequency is set, try to infer from time differences
    if len(index) < 2:
        return 'D'  # Default to day if we can't determine
    
    # Calculate time differences in nanoseconds
    time_diffs = np.diff(index.astype(np.int64))
    
    # Print debugging information
    _print_if_verbose("Unique time differences and their counts:", verbose)
    _print_if_verbose(pd.Series(time_diffs).value_counts(), verbose)
    
    # Use pandas value_counts instead of np.bincount for memory efficiency
    most_common_diff = pd.Series(time_diffs).value_counts().index[0]
    _print_if_verbose(f"\nMost common difference: {most_common_diff} nanoseconds", verbose)
    
    # Convert to timedelta and check
    td = pd.Timedelta(most_common_diff, unit='ns')
    _print_if_verbose(f"Converted to timedelta: {td}", verbose)
    
    if td <= pd.Timedelta(hours=1):
        return 'H'
    elif td <= pd.Timedelta(days=1):
        return 'D'
    elif td <= pd.Timedelta(weeks=1):
        return 'W'
    else:
        return 'M'


def _calculate_search_granularity(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    verbose: bool = False
) -> Dict[str, Union[str, pd.DatetimeIndex]]:
    """
    Calculate the appropriate granularity for a Google Trends search based on the time range
    and generate the corresponding DateTimeIndex.
    
    Args:
        start_date (Union[str, datetime]): Start date of the search
        end_date (Union[str, datetime]): End date of the search
        verbose (bool): Whether to print debug information
        
    Returns:
        Dict[str, Union[str, pd.DatetimeIndex]]: Dictionary containing:
            - "granularity": The appropriate granularity to use ("day", "week", or "month")
            - "index": A pandas DateTimeIndex with the appropriate frequency
    """
    # Convert dates to datetime if they're strings
    if isinstance(start_date, str):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = start_date
        
    if isinstance(end_date, str):
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = end_date
    
    # Calculate the time range in days
    days_diff = (end_dt - start_dt).days
    
    # Determine granularity based on time range
    if days_diff <= 270:  # Up to and including 270 days
        granularity = "day"
        freq = 'D'
    elif 270 < days_diff <= 365:  # Between 270 days and 1 year
        granularity = "week"
        freq = 'W'
    else:  # More than 1 year
        granularity = "month"
        freq = 'M'
    
    # Create DateTimeIndex with appropriate frequency, ensuring both start and end dates are included
    index = pd.date_range(start=start_dt, end=end_dt, freq=freq, inclusive='both')
    
    if verbose:
        _print_if_verbose(f"Granularity for date range {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} ({days_diff} days) is {granularity}", verbose)
    
    return {
        "granularity": granularity,
        "index": index
    }


def _custom_mode(df: pd.DataFrame, axis: int = 1) -> pd.Series:
    """
    Calculate mode of a DataFrame, returning mean of modes if multiple exist.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        axis (int): Axis along which to calculate mode (0 for columns, 1 for rows)
        
    Returns:
        pd.Series: Series containing mode values (or mean of modes if multiple exist)
    """
    # Get modes using pandas mode()
    modes = df.mode(axis=axis)
    # Calculate mean of modes along the same axis
    return modes.mean(axis=axis)


def _numbered_file_name(orig_name: str, n_digits: int = 3, path: Optional[str] = None) -> str:
    """
    Generate a numbered filename by finding the next available number in the directory.
    If filename ends with _i### pattern, use the next available number. If no number pattern exists,
    add _i### pattern with specified digits. Number of digits is enforced in both cases.
    
    Args:
        orig_name (str): The original filename
        n_digits (int): Number of digits to use for the counter. Defaults to 3
        path (str, optional): Directory path to search for existing files. Defaults to None (current directory)
        
    Returns:
        str: New filename with the next available number
    """
    # Split the filename into base name and extension
    base_name, ext = os.path.splitext(orig_name)
    
    # Remove any existing _i### pattern to get the base name
    base_name = re.sub(r'_i\d+$', '', base_name)
    
    # Get all files in the specified directory
    search_path = path if path else '.'
    existing_files = [f for f in os.listdir(search_path) if os.path.isfile(os.path.join(search_path, f))]
    
    # Find the highest existing number
    max_number = 0
    pattern = re.compile(f"{base_name}_i(\\d+){ext}$")
    
    for file in existing_files:
        match = pattern.match(file)
        if match:
            number = int(match.group(1))
            max_number = max(max_number, number)
    
    # Use the next available number
    next_number = max_number + 1
    
    # Create the new filename with _i and enforced n_digits pattern
    new_name = f"{base_name}_i{next_number:0{n_digits}d}{ext}"
    
    return new_name


def save_to_csv(
    combined_df: pd.DataFrame,
    search_term: str,
    path: Optional[str] = None,
    comment: Optional[str] = None,
    verbose: bool = False
) -> str:
    """
    Save the dataframe to a CSV file.
    
    Args:
        combined_df (pd.DataFrame): The dataframe to save
        search_term (str): The search term used to generate the data
        path (Optional[str]): Directory path to save the file. Defaults to None (current directory)
        comment (Optional[str]): Comment to add at the top of the file. Defaults to None
        verbose (bool): Whether to print debug information
        
    Returns:
        str: The filename that was created
    """
    # Create a filename with the search term and current ISO date
    current_date = datetime.now().strftime("%Y-%m-%d")
    formatted_utc_gmtime = time.strftime("%Y-%m-%dT%H-%MUTC", time.gmtime())

    # Replace spaces with underscores in the search term for the filename
    safe_search_term = search_term.replace(" ", "_")
    filename = f"{safe_search_term}_at_{formatted_utc_gmtime}.csv"
    filename = _numbered_file_name(filename, path=path)
    
    # Join path if provided, otherwise use filename directly
    full_path = os.path.join(path, filename) if path else filename
    
    # First write the comment if provided
    if comment:
        with open(full_path, 'w') as f:
            f.write(f"# {comment}\n")
    
    # Save the dataframe to the CSV file
    combined_df.to_csv(full_path, index=True, mode='a')
    _print_if_verbose(f"\nData saved to {full_path}", verbose)
    return filename


def _get_total_size(obj: Any, seen: Optional[set] = None) -> int:
    """
    Calculate the total memory size of an object, including all nested objects.
    
    Args:
        obj: The object to measure
        seen: Set of object IDs already seen (to prevent infinite recursion)
        
    Returns:
        int: Total size in bytes
    """
    if seen is None:
        seen = set()
        
    obj_id = id(obj)
    if obj_id in seen:
        return 0
        
    seen.add(obj_id)
    size = sys.getsizeof(obj)
    
    # Handle different types of objects
    if isinstance(obj, dict):
        size += sum(_get_total_size(v, seen) + _get_total_size(k, seen) 
                   for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set)):
        size += sum(_get_total_size(item, seen) for item in obj)
    elif hasattr(obj, '__dict__'):
        # Handle custom objects
        size += _get_total_size(obj.__dict__, seen)
    elif hasattr(obj, 'items'):
        # Handle pandas/numpy objects that have items() method
        size += sum(_get_total_size(v, seen) + _get_total_size(k, seen) 
                   for k, v in obj.items())
        
    return size


def _get_start_date_of_pair(date_str: str) -> str:
    """
    Extract the start date from a date range string.
    
    Args:
        date_str (str): Date range string in format like "Dec 31, 2023 – Jan 6, 2024" or "Jan 7 – 13, 2024"
        
    Returns:
        str: The start date as a string in YYYY-MM-DD format
        
    Raises:
        ValueError: If the date string cannot be parsed
    """
    # First clean the unicode to ascii because serpapi returns some weird unicode characters
    date_str = unicodedata.normalize('NFKC', date_str)
    
    # By default we will return the original date string
    original_date_str = date_str
    
    parts = date_str.split(" – ")
    
    # Handle case with full date range (e.g. "Dec 31, 2023 – Jan 6, 2024")
    if "," in parts[0]:
        original_date_str = parts[0]
    elif len(parts) == 2:
        start_date = parts[0]
        # Extract year from end date
        year = parts[1].split(", ")[1]
        original_date_str = f"{start_date}, {year}"
        
    # Convert the date string to basically ISO format
    try:
        datetime_object = datetime.strptime(original_date_str, "%b %d, %Y")
    except ValueError:
        try:
            datetime_object = datetime.strptime(original_date_str, "%m/%d/%Y")
        except ValueError:
            try:
                datetime_object = datetime.strptime(original_date_str, "%b %Y")
            except ValueError:
                raise ValueError(f"Could not parse date string: {original_date_str}")
    
    output_date_str = datetime_object.strftime("%Y-%m-%d")
    return output_date_str


class Trends:
    def __init__(
        self,
        serpapi_api_key: Optional[str] = None,
        serpwow_api_key: Optional[str] = None,
        searchapi_api_key: Optional[str] = None,
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
    ):
        """
        Initialize the Trends class with configuration parameters.
        
        Args:
            serpapi_api_key (Optional[str]): Your SerpAPI API key. If provided, will use SerpAPI
            serpwow_api_key (Optional[str]): Your SerpWow API key. If provided, will use SerpWow
            searchapi_api_key (Optional[str]): Your SearchApi API key. If provided, will use SearchApi
            no_cache (bool): Whether to skip cached results (only used with SerpAPI)
            proxy (Optional[str]): The proxy to use. If None, no proxy will be used
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
            api (Optional[str]): Which API to use ("serpapi", "serpwow", "searchapi", or "trendspy"). If None, will auto-select based on available keys.
        """
        # Use provided keys or fall back to defaults from keys.py
        self.serpapi_api_key = serpapi_api_key if serpapi_api_key is not None else SERPAPI_API_KEY
        self.serpwow_api_key = serpwow_api_key if serpwow_api_key is not None else SERPWOW_API_KEY
        self.searchapi_api_key = searchapi_api_key if searchapi_api_key is not None else SEARCHAPI_API_KEY
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
        self.search_log = []  # List to store search information
        self.api = api  # Store the chosen API


    def search(
        self,
        search_term: str,
        start_date: str,
        end_date: Optional[str] = None,
        duration_days: Optional[int] = 90,
        granularity: str = "day",
        n_iterations: int = 1,
        stagger: int = 0,
        trim: bool = True,
        scale: bool = True,
        combine: str = "median",
        final_scale: bool = True,
        round: int = 2,
        method: str = "MAD"
    ) -> pd.DataFrame:
        """
        Search Google Trends for a given query, with optional multiple iterations.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_date (str): Start date for the search (e.g. "2008-01-01")
            end_date (Optional[str]): End date for the search (e.g. "2025-04-21")
            duration_days (Optional[int]): Number of days to search from start_date if end_date not provided
            granularity (str): Time granularity for results, either "day" or "hour". Any other value will use the default API behavior.
            n_iterations (int): Number of times to perform the search. Defaults to 1
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            trim (bool): Whether to drop rows with NA values because of the staggering. Defaults to True.
            scale (bool): Whether to scale overlapping intervals. Defaults to True.
            combine (str): How to combine multiple columns. Options are "mean", "median", or "mode". Defaults to "median".
            final_scale (bool): Whether to scale the final result so maximum value is 100. Defaults to True.
            round (int): Number of decimal places to round values to. Defaults to 2.
            method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
            
        Returns:
            pd.DataFrame: DataFrame containing the Google Trends data
            
        Note:
            - If n_iterations > 1, the results will be combined using the specified combine method
            - The combine method can be "mean", "median", or "mode"
            - All other parameters are passed through to the underlying search methods
        """
        # Validate combine parameter
        if combine not in ["none", "mean", "median", "mode"]:
            raise ValueError(f"Invalid combine method: {combine}. Must be one of: none, mean, median, mode")
            
        # Determine time range
        if end_date is None:
            time_range = None  # Will be handled by search_by_day_270
        else:
            time_range = f"{start_date} {end_date}"
        
        prefix = "[DRY RUN] " if self.dry_run else ""
        message = (
            f"{prefix}Preparing to perform search with:\n"
            f"  Search term: {search_term}\n"
            f"  Start date: {start_date}\n"
            f"  End date: {end_date if end_date else 'None (using duration_days=' + str(duration_days) + ')'}\n"
            f"  Granularity: {granularity}\n"
            f"  Iterations: {n_iterations}\n"
            f"  Stagger: {stagger}\n"
            f"  Scale: {scale}\n"
            f"  Combine: {combine}\n"
            f"  Final scale: {final_scale}\n"
            f"  Round: {round}\n"
            f"  Method: {method}\n"
            f"  Geo: {self.geo}\n"
            f"  Category: {self.cat}"
        )
        api_name = self._select_api()
        message += f"\n  Using API: {api_name}"
        self._print(message)
        
        all_timeseries = []
        self._print(f"Collecting {n_iterations} timeseries for '{search_term}'...")
    
        for i in range(n_iterations):
            self._print(f"Iteration {i+1}/{n_iterations}")
        
            # Choose appropriate search function based on parameters
            if end_date is None:
                iteration_results = self.search_by_day_270(
                    search_term=search_term,
                    start_date=start_date
                )
            elif granularity == "day":
                iteration_results = self.search_by_day(
                    search_term=search_term,
                    time_range=time_range,
                    stagger=stagger,
                    trim=trim,
                    scale=scale,
                    combine=combine,
                    final_scale=final_scale,
                    round=round,
                    method=method
                )
            elif granularity == "hour":
                iteration_results = self.search_by_hour(
                    search_term=search_term,
                    time_range=time_range
                )
            else:
                iteration_results = self._search_with_chosen_api(
                    search_term=search_term,
                    time_range=time_range
                )
        
            all_timeseries.append(iteration_results)
    
        # If only one iteration, return the single result
        if n_iterations == 1:
            return all_timeseries[0]
    
        # Combine multiple iterations into a single dataframe
        combined_df = pd.DataFrame()
        safe_search_term = search_term.replace(" ", "_")

        for i, df in enumerate(all_timeseries):
            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])
            combined_df[f"iter_{i+1}"] = df[safe_search_term]

        self._print(f"Combined df for '{search_term}' shape: {combined_df.shape}")
        
        # Combine columns using the specified method
        if combine == "mean":
            result = pd.DataFrame(combined_df.mean(axis=1), columns=[safe_search_term])
        elif combine == "median":
            result = pd.DataFrame(combined_df.median(axis=1), columns=[safe_search_term])
        elif combine == "mode":
            result = pd.DataFrame(self._custom_mode(combined_df, axis=1), 
                                index=combined_df.index,
                                columns=[safe_search_term])
        elif combine == "none":
            result = combined_df

        # Print search log summary
        prefix = "[DRY RUN] " if self.dry_run else ""
        message = (
            f"\n{prefix}Search Summary:\n"
            f"Total searches performed: {len(self.search_log)}\n"
            f"API used: {api_name}\n"
            "\nSearch details:"
        )
        for i, log in enumerate(self.search_log, 1):
            error_str = f" [ERROR: {log['error']}]" if 'error' in log else ""
            warning_str = f" [WARNING: {log['warning']}]" if 'warning' in log else ""
            message += f"\nSearch {i}: {log['search_term']} | {log['time_range']} | {log['api']} | {log['granularity']}{error_str}{warning_str}"
        self._print(message)
        
        return result

    def search_by_day(
        self,
        search_term: str,
        time_range: str,
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
        Perform a Google Trends search with daily granularity over multiple 270-day intervals.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            time_range (str): Time range for the search (e.g. "2008-01-01 2025-04-21")
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            trim (bool): Whether to drop rows with NA values because of the staggering. Defaults to True.
            scale (bool): Whether to scale overlapping intervals. Defaults to True.
            combine (str): How to combine multiple columns. Options are "none", "mean", "median", or "mode". Defaults to "median".
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
            f"  Time range: {time_range}\n"
            f"  Stagger: {stagger}\n"
            f"  Scale: {scale}\n"
            f"  Method: {method}\n"
            f"  Combine: {combine}\n"
            f"  Final scale: {final_scale}\n"
            f"  Round: {round}\n"
            f"  API: {self.api if hasattr(self, 'api') and self.api else 'auto-select'}"
        )
        self._print(message)
        
        # Parse the time range
        start_date, end_date = time_range.split()
        
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
            if self.dry_run:
                # Create a date range for the entire period
                date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
                result = pd.DataFrame(0, index=date_range, columns=[search_term.replace(" ", "_")])
            else:
                result = self.search_by_day_270(
                    search_term=search_term,
                    start_date=start_dt
                )
            return result
        
        # For ranges longer than 270 days, use staggered searches
        stagger_groups = self.search_staggered(
            search_term=search_term,
            start_dt=start_dt,
            end_dt=end_dt,
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
            prefix = "[DRY RUN] " if self.dry_run else ""
            message = (
                f"\n{prefix}Search Summary:\n"
                f"Total searches performed: {len(self.search_log)}\n"
                f"API used: {self._select_api()}\n"
                "\nSearch details:"
            )
            for i, log in enumerate(self.search_log, 1):
                error_str = f" [ERROR: {log['error']}]" if 'error' in log else ""
                warning_str = f" [WARNING: {log['warning']}]" if 'warning' in log else ""
                message += f"\nSearch {i}: {log['search_term']} | {log['time_range']} | {log['api']} | {log['granularity']}{error_str}{warning_str}"
            self._print(message)

            return result_df
        return pd.DataFrame()

    def search_by_day_270(
        self,
        search_term: str,
        start_date: Union[str, datetime]
    ) -> pd.DataFrame:
        """
        Perform a Google Trends search with daily granularity over a 270-day period.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_date (Union[str, datetime]): The start date in YYYY-MM-DD format or datetime object
            
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
        end_date = end_dt.strftime("%Y-%m-%d")
        
        # Create the time range string
        time_range = f"{start_dt.strftime('%Y-%m-%d')} {end_date}"
        
        # Get the API name for logging
        api_name = self._select_api()
        
        # Perform the search using the chosen API
        results = self._search_with_chosen_api(
            search_term=search_term,
            time_range=time_range
        )
        
        # If results is a DataFrame, validate its granularity
        if isinstance(results, pd.DataFrame):
            actual_granularity = self._get_index_granularity(results.index)
            if actual_granularity != 'D':
                warning_msg = f"Expected daily granularity but got {actual_granularity}"
                # Print warning immediately with detailed information
                self._print(f"\nWARNING: {warning_msg}")
                self._print(f"  Search term: {search_term}")
                self._print(f"  Time range: {time_range}")
                self._print(f"  API used: {api_name}")
                # Log the warning
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range,
                    api=api_name,
                    granularity=actual_granularity,
                    warning=warning_msg
                )
        
        return results

    def search_by_hour(
        self,
        search_term: str,
        time_range: str
    ) -> pd.DataFrame:
        """
        Perform a Google Trends search with hourly granularity over a 7-day period.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            time_range (str): Time range for the search (e.g. "2008-01-01 2025-04-21")
            
        Returns:
            pd.DataFrame: A dataframe containing the timeseries data with hourly granularity
        """
        # Parse the time range
        start_date, end_date = time_range.split()
        
        # Convert start_date to datetime if it's a string, otherwise use as is
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_dt = start_date
        
        # Calculate end_date (7 days later, non-inclusive)
        end_dt = start_dt + timedelta(days=7) - timedelta(hours=1)

        if self.dry_run:
            # Create a date range with hourly frequency
            date_range = pd.date_range(start=start_dt, end=end_dt, freq='H')
            result = pd.DataFrame(0, index=date_range, columns=[search_term.replace(" ", "_")])
            return result

        # Convert to ISO format strings
        start_date = start_dt.strftime("%Y-%m-%dT%H")
        end_date = end_dt.strftime("%Y-%m-%dT%H")
        
        # Create the time range string
        time_range = f"{start_date} {end_date}"
        
        # Perform the search using the chosen API
        results = self._search_with_chosen_api(
            search_term=search_term,
            time_range=time_range
        )
        
        return results

    def search_staggered(
        self,
        search_term: str,
        start_dt: datetime,
        end_dt: datetime,
        stagger: int = 0,
        scale: bool = True,
        method: str = "MAD"
    ) -> List[List[pd.DataFrame]]:
        """
        Perform staggered searches over multiple 270-day intervals.
        
        Args:
            search_term (str): The search term to look up in Google Trends
            start_dt (datetime): Start date for the search
            end_dt (datetime): End date for the search
            stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                          2 means 67% overlap, etc.
            scale (bool): Whether to scale overlapping intervals. Defaults to True.
            method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
            
        Returns:
            List[List[pd.DataFrame]]: List of stagger groups, each containing a list of dataframes.
            Each dataframe contains 270 days of data with daily granularity.
            
        Note:
            - Each interval is exactly 270 days long
            - If stagger > 0, intervals will overlap according to the stagger factor
            - If scale is True, overlapping intervals will be scaled to minimize differences
            - In dry run mode, returns dummy dataframes with zero values
            - Uses instance properties dry_run and verbose for execution control
        """
        # Calculate number of 270-day intervals needed
        total_days = (end_dt - start_dt).days
        base_intervals = math.ceil(total_days / 270)
        
        # Calculate overlap factor
        if stagger == 0:
            overlap_factor = 0
        else:
            overlap_factor = 1 / (stagger + 1)
        
        # Calculate stagger days
        stagger_days = math.floor(270 * overlap_factor)
        
        # Create list to store results for each stagger group
        stagger_groups = [[] for _ in range(stagger + 1)]
        
        # Initialize search counter
        search_count = 0
        
        # For each stagger group
        for s in range(stagger + 1):
            # Calculate current start based on stagger days
            current_start = start_dt - timedelta(days=(stagger - s) * stagger_days)
            
            # Calculate how many intervals we need for this group
            # For the last group, we need base_intervals
            # For other groups, we need base_intervals + 1
            intervals_needed = base_intervals if s == stagger else base_intervals + 1
            
            # Collect intervals for this stagger group
            for i in range(intervals_needed):
                search_count += 1
                if self.dry_run:
                    # Create a 270-day range for this interval
                    interval_end = current_start + timedelta(days=269)
                    interval_range = pd.date_range(start=current_start, end=interval_end, freq='D')
                    result = pd.DataFrame(0, index=interval_range, columns=[search_term.replace(" ", "_")])
                else:
                    result = self.search_by_day_270(
                        search_term=search_term,
                        start_date=current_start
                    )
                
                # Check for error in result
                if isinstance(result, dict):
                    result['search_count'] = search_count
                    self._print(f"Error in search: {result}")
                    return []
                
                stagger_groups[s].append(result)
                current_start = current_start + timedelta(days=270)
        
        if self.dry_run:
            self._print(f"[DRY RUN] Would perform {search_count} searches:")
            for s, group in enumerate(stagger_groups):
                for i, df in enumerate(group):
                    start_date = df.index[0].strftime('%Y-%m-%d')
                    end_date = df.index[-1].strftime('%Y-%m-%d')
                    self._print(f"Group {s+1}, Interval {i+1}: {start_date} to {end_date}")
        
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

    def _log_api_search(
        self,
        search_term: str,
        time_range: str,
        api: str,
        granularity: str,
        error: Optional[str] = None,
        warning: Optional[str] = None
    ) -> None:
        """
        Log a search attempt with its details and any errors.
        
        Args:
            search_term (str): The search term used
            time_range (str): The time range string sent to the API
            api (str): The API used for the search ("SerpAPI", "SerpWow", or "trendspy")
            granularity (str): The granularity of the data ('H', 'D', 'W', or 'M')
            error (Optional[str]): Any error message if the search failed
            warning (Optional[str]): Any warning message about the search results
        """
        formatted_utc_gmtime = time.strftime("%Y-%m-%dT%H-%MUTC", time.gmtime())
        log_entry = {
            "search_term": search_term,
            "time_range": time_range,
            "search_time": formatted_utc_gmtime,
            "api": api,
            "granularity": granularity
        }
        if error:
            log_entry["error"] = error
        if warning:
            log_entry["warning"] = warning
        self.search_log.append(log_entry)

    def _log_search(
        self,
        search_term: str,
        time_range: str,
        api: str,
        granularity: str,
        error: Optional[str] = None,
        warning: Optional[str] = None
    ) -> None:
        """
        Log a search attempt with its details and any errors.
        
        Args:
            search_term (str): The search term used
            time_range (str): The time range string sent to the API
            api (str): The API used for the search ("SerpAPI", "SerpWow", or "trendspy")
            granularity (str): The granularity of the data ('H', 'D', 'W', or 'M')
            error (Optional[str]): Any error message if the search failed
            warning (Optional[str]): Any warning message about the search results
        """
        self._log_api_search(search_term, time_range, api, granularity, error, warning)


    def _select_api(self) -> str:
        """
        Determine which API to use based on available API keys.
        
        Returns:
            str: The name of the API to use ("serpapi", "serpwow", "searchapi", or "trendspy")
            
        Raises:
            ValueError: If the chosen API's key is not available
        """
        # Check if a specific API was chosen
        if self.api is not None:  # Changed from hasattr(self, 'api') and self.api
            if self.api == "serpapi":
                if not self.serpapi_api_key:
                    raise ValueError("SerpAPI key not available")
                return "serpapi"
            elif self.api == "serpwow":
                if not self.serpwow_api_key:
                    raise ValueError("SerpWow key not available")
                return "serpwow"
            elif self.api == "searchapi":
                if not self.searchapi_api_key:
                    raise ValueError("SearchAPI key not available")
                return "searchapi"
            elif self.api == "trendspy":
                return "trendspy"
            else:
                raise ValueError(f"Invalid API specified: {self.api}. Must be one of: serpapi, serpwow, searchapi, trendspy")
            
        # Auto-select API based on available keys
        if self.serpapi_api_key:
            return "serpapi"
        elif self.serpwow_api_key:
            return "serpwow"
        elif self.searchapi_api_key:
            return "searchapi"
        else:
            return "trendspy"

    def _search_with_chosen_api(
        self,
        search_term: Union[str, List[str]],
        time_range: Optional[str] = None
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """
        Perform a search using the appropriate API based on available API keys.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            time_range (Optional[str]): Time range for the search
            
        Returns:
            Union[pd.DataFrame, Dict[str, Any]]: Either a DataFrame with the trends data or a dict containing an error message
        """
        api_name = self._select_api()
        if api_name == "serpapi":
            return self._search_serpapi(search_term=search_term, time_range=time_range)
        elif api_name == "serpwow":
            return self._search_serpwow(search_term=search_term, time_range=time_range)
        elif api_name == "searchapi":
            return self._search_searchapi(search_term=search_term, time_range=time_range)
        else:  # trendspy
            return self._search_trendspy(search_term=search_term, time_range=time_range)

    
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


    def _change_tor_identity(self):
        """
        Change the Tor identity by connecting to the Tor control port and sending a NEWNYM signal.
        Includes error handling and retry logic.
        """
        try:
            from stem.control import Controller
            from stem import Signal
        except ImportError:
            print("Error: stem library not installed. Please install it with 'pip install stem'")
            return
        
        password="controlpass" # This is the password for the Tor control port

        try:
            # Try to connect to the Tor control port
            with Controller.from_port(port=9051) as controller:
                # Authenticate with the controller
                controller.authenticate(password=password)
                
                # Send the NEWNYM signal to change the identity
                controller.signal(Signal.NEWNYM)
                print("Tor identity changed successfully.")
                
                # Wait a moment to ensure the change takes effect
                time.sleep(2)
                
        except socket.error as e:
            print(f"Socket error connecting to Tor control port: {e}")
            print("Make sure Tor is running with control port enabled.")
            print("Add 'ControlPort 9051' to your torrc file and restart Tor.")
        except Exception as e:
            print(f"Error changing Tor identity: {e}")

    def _search_trendspy(
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
        self._print(f"Sending trendspy search request:")
        self._print(f"  Search term: {search_term}")
        self._print(f"  Time range: {time_range if time_range else 'default'}")
        self._print(f"  Proxy: {self.proxy or 'None'}")
        self._print(f"  Change identity: {self.change_identity}")
        
        try:
            # Format proxy for trendspy
            proxy = None
            if self.proxy:
                # Add timeout and verify settings
                proxy = {
                    "http": f"socks5h://{self.proxy}",
                    "https": f"socks5h://{self.proxy}"
                }
                # Test proxy connection before proceeding
                try:
                    test_response = requests.get('https://www.google.com', 
                                              proxies=proxy, 
                                              timeout=10)
                    test_response.raise_for_status()
                except Exception as e:
                    self._print(f"  Proxy connection test failed: {str(e)}")
                    self._print(f"  Note: If using Tor Browser, make sure it's running and the SOCKS proxy is enabled")
                    raise ValueError(f"Failed to connect to proxy {self.proxy}: {str(e)}")
            
            # Create trendspy instance with retry settings
            trends = trendspy.Trends(
                proxy=proxy,
                request_delay=self.request_delay,
                geo=self.geo,
                cat=self.cat
            )
            
            # Prepare the parameters for interest_over_time
            params = {}
            if time_range:
                params['timeframe'] = time_range
            
            # Perform the search with the appropriate parameters
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    # If change_identity is True, change the Tor identity before each attempt
                    if self.change_identity:
                        self._print(f"  Changing Tor identity for attempt {attempt + 1}")
                        self._change_tor_identity()
                    
                    results = trends.interest_over_time(search_term, **params)
                    self._print("  Search successful!")
                    
                    # Log the search
                    self._log_api_search(
                        search_term=search_term,
                        time_range=time_range if time_range else "default",
                        api="trendspy",
                        granularity=self._get_index_granularity(results.index)
                    )
                    
                    return results
                except Exception as e:
                    if attempt < max_retries - 1:
                        self._print(f"  Attempt {attempt + 1} failed: {str(e)}")
                        self._print(f"  Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        self._print(f"  All {max_retries} attempts failed")
                        raise
                        
        except Exception as e:
            self._print(f"  Search failed: {str(e)}")
            raise

    def _search_serpapi(
        self,
        search_term: Union[str, List[str]],
        time_range: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Search Google Trends using the SerpAPI.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            time_range (Optional[str]): Time range for the search
            
        Returns:
            pd.DataFrame: A dataframe containing the timeseries data
        """
        self._print(f"Sending SerpAPI search request:")
        self._print(f"  Search term: {search_term}")
        self._print(f"  Time range: {time_range if time_range else 'default'}")
        
        try:
            from serpapi import GoogleSearch
            
            # Set up the request parameters
            params = {
                "api_key": self.serpapi_api_key,
                "engine": "google_trends",
                "no_cache": str(self.no_cache).lower(),
                "q": search_term,
                "hl": self.language,
                "geo": self.geo,
                "date": time_range,
                "tz": str(self.tz)
            }
            
            # Add optional parameters if provided
            if self.cat is not None:
                params["cat"] = str(self.cat)
            if self.region:
                params["region"] = self.region
            
            # Make the API request
            search = GoogleSearch(params)
            data = search.get_dict()
            # # Print the full response for debugging
            # self._print("\nFull API response:")
            # self._print(json.dumps(data, indent=2)[:10000])  # Increased from 2000 to 10000
                        # Check if there's an error in the results
            if isinstance(data, dict) and "error" in data:
                error_msg = data["error"]
                self._print(f"  Search failed: {error_msg}")
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range if time_range else "default",
                    api="serpapi",
                    granularity="D",
                    error=error_msg
                )
                return pd.DataFrame()
            
            # Extract the trends data
            if 'interest_over_time' in data and 'timeline_data' in data['interest_over_time']:
                timeline_data = data['interest_over_time']['timeline_data']
                
                if not timeline_data:
                    error_msg = "No trends data found in response"
                    self._print(f"  Search failed: {error_msg}")
                    self._log_api_search(
                        search_term=search_term,
                        time_range=time_range if time_range else "default",
                        api="serpapi",
                        granularity="D",
                        error=error_msg
                    )
                    return pd.DataFrame()
                
                # Create lists to store dates and values
                dates = []
                values = []
                
                # Process each data point
                for point in timeline_data:
                    # Convert timestamp to datetime
                    date = datetime.fromtimestamp(int(point['timestamp']))
                    dates.append(date)
                    
                    # Get the value for the search term
                    if point['values'] and point['values'][0]['extracted_value'] is not None:
                        value = point['values'][0]['extracted_value']
                    else:
                        value = 0
                    values.append(value)
                
                # Create DataFrame
                df = pd.DataFrame({
                    search_term.replace(" ", "_"): values
                }, index=pd.DatetimeIndex(dates))
                
                self._print("  Search successful!")
                
                # Log the search
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range if time_range else "default",
                    api="serpapi",
                    granularity=self._get_index_granularity(df.index)
                )
                
                return df
            else:
                error_msg = "No trends data found in response"
                self._print(f"  Search failed: {error_msg}")
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range if time_range else "default",
                    api="serpapi",
                    granularity="D",
                    error=error_msg
                )
                return pd.DataFrame()
                
        except Exception as e:
            self._print(f"  Search failed: {str(e)}")
            self._log_api_search(
                search_term=search_term,
                time_range=time_range if time_range else "default",
                api="serpapi",
                granularity="D",
                error=str(e)
            )
            raise

    def _search_serpwow(
        self,
        search_term: Union[str, List[str]],
        time_range: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Search Google Trends using the SerpWow API.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            time_range (Optional[str]): Time range for the search (e.g. "2008-01-01 2025-04-21")
            
        Returns:
            pd.DataFrame: A dataframe containing the timeseries data
        """
        self._print(f"Sending SerpWow search request:")
        self._print(f"  Search term: {search_term}")
        self._print(f"  Time range: {time_range if time_range else 'default'}")
        
        try:
            # Parse time range if provided
            if time_range:
                start_date, end_date = time_range.split()
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
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
                'api_key': self.serpwow_api_key,
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
            
            # Add optional parameters if provided
            if self.cat is not None:
                params['trends_category'] = str(self.cat)
            if self.region:
                params['trends_region'] = self.region
            
            # Print the full request URL (with API key masked)
            masked_params = params.copy()
            masked_params['api_key'] = '***'
            request_url = 'https://api.serpwow.com/live/search'
            self._print(f"\nFull request URL (API key masked):")
            self._print(f"  {request_url}?{'&'.join(f'{k}={v}' for k, v in masked_params.items())}")
            
            # Make the HTTP GET request
            response = requests.get(request_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Parse the JSON response
            data = response.json()
            
            # # Print the full response for debugging
            # self._print("\nFull API response:")
            # self._print(json.dumps(data, indent=2)[:10000])  # Increased from 2000 to 10000
            
            # Check for API errors
            if 'error' in data:
                error_msg = data['error']
                self._print(f"  Search failed: {error_msg}")
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range if time_range else f"{start_dt.strftime('%Y-%m-%d')} {end_dt.strftime('%Y-%m-%d')}",
                    api="serpwow",
                    granularity="D",
                    error=error_msg
                )
                return pd.DataFrame()
            
            # Extract the trends data
            if 'trends_interest_over_time' in data and 'data' in data['trends_interest_over_time']:
                timeline_data = data['trends_interest_over_time']['data']
                
                if not timeline_data:
                    error_msg = "No trends data found in response"
                    self._print(f"  Search failed: {error_msg}")
                    self._log_api_search(
                        search_term=search_term,
                        time_range=time_range if time_range else f"{start_dt.strftime('%Y-%m-%d')} {end_dt.strftime('%Y-%m-%d')}",
                        api="serpwow",
                        granularity="D",
                        error=error_msg
                    )
                    return pd.DataFrame()
                
                # Create lists to store dates and values
                dates = []
                values = []
                
                # Process each data point
                for point in timeline_data:
                    # Convert UTC date to datetime
                    date = datetime.strptime(point['date_utc'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    dates.append(date)
                    
                    # Get the value for the search term
                    if point['values'] and point['values'][0]['has_value']:
                        value = point['values'][0]['value']
                    else:
                        value = 0
                    values.append(value)
                
                # Create DataFrame
                df = pd.DataFrame({
                    search_term.replace(" ", "_"): values
                }, index=pd.DatetimeIndex(dates))
                
                self._print("  Search successful!")
                
                # Log the search
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range if time_range else f"{start_dt.strftime('%Y-%m-%d')} {end_dt.strftime('%Y-%m-%d')}",
                    api="serpwow",
                    granularity=self._get_index_granularity(df.index)
                )
                
                return df
            else:
                error_msg = "No trends data found in response"
                self._print(f"  Search failed: {error_msg}")
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range if time_range else f"{start_dt.strftime('%Y-%m-%d')} {end_dt.strftime('%Y-%m-%d')}",
                    api="serpwow",
                    granularity="D",
                    error=error_msg
                )
                return pd.DataFrame()
                
        except Exception as e:
            self._print(f"  Search failed: {str(e)}")
            self._log_api_search(
                search_term=search_term,
                time_range=time_range if time_range else f"{start_dt.strftime('%Y-%m-%d')} {end_dt.strftime('%Y-%m-%d')}",
                api="serpwow",
                granularity="D",
                error=str(e)
            )
            raise

    def _search_searchapi(
        self,
        search_term: Union[str, List[str]],
        time_range: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Search Google Trends using the SearchAPI.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            time_range (Optional[str]): Time range for the search (e.g. "2008-01-01 2025-04-21")
            
        Returns:
            pd.DataFrame: A dataframe containing the timeseries data
            
        Note:
            SearchAPI supports up to 5 search queries separated by commas.
            Time range can be specified in various formats:
            - "now 1-H" for past hour
            - "now 4-H" for past 4 hours
            - "now 1-d" for past day
            - "now 7-d" for past 7 days
            - "today 1-m" for past 30 days
            - "today 3-m" for past 90 days
            - "today 12-m" for past 12 months
            - "today 5-y" for past 5 years
            - "all" for all available data since 2004
            - Custom date range: "yyyy-mm-dd yyyy-mm-dd"
        """
        self._print(f"Sending SearchAPI search request:")
        self._print(f"  Search term: {search_term}")
        self._print(f"  Time range: {time_range if time_range else 'default'}")
        
        try:
            # Set up the request parameters
            params = {
                'engine': 'google_trends',
                'api_key': self.searchapi_api_key,
                'data_type': 'TIMESERIES',
                'q': search_term,
                'geo': self.geo,
                'tz': str(self.tz),
                'language': self.language
            }
            
            # Add time range if provided
            if time_range:
                params['time'] = time_range
            
            # Add optional parameters if provided
            if self.cat is not None:
                params['cat'] = str(self.cat)
            if self.region:
                params['region'] = self.region
            
            # Make the HTTP GET request
            response = requests.get('https://www.searchapi.io/api/v1/search', params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Parse the JSON response
            data = response.json()
            # # Print the full response for debugging
            # self._print("\nFull API response:")
            # self._print(json.dumps(data, indent=2)[:10000])  # Increased from 2000 to 10000
            
            # Extract the trends data
            if 'interest_over_time' in data and 'timeline_data' in data['interest_over_time']:
                timeline_data = data['interest_over_time']['timeline_data']
                
                if not timeline_data:
                    error_msg = "No trends data found in response"
                    self._print(f"  Search failed: {error_msg}")
                    self._log_api_search(
                        search_term=search_term,
                        time_range=time_range if time_range else "default",
                        api="searchapi",
                        granularity="D",
                        error=error_msg
                    )
                    return pd.DataFrame()
                
                # Create lists to store dates and values
                dates = []
                values = []
                
                # Process each data point
                for point in timeline_data:
                    # Convert timestamp to datetime
                    date = datetime.fromtimestamp(int(point['timestamp']))
                    dates.append(date)
                    
                    # Get the value for the search term
                    if point['values'] and point['values'][0]['extracted_value'] is not None:
                        value = point['values'][0]['extracted_value']
                    else:
                        value = 0
                    values.append(value)
                
                # Create DataFrame
                df = pd.DataFrame({
                    search_term.replace(" ", "_"): values
                }, index=pd.DatetimeIndex(dates))
                
                self._print("  Search successful!")
                
                # Log the search
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range if time_range else "default",
                    api="searchapi",
                    granularity=self._get_index_granularity(df.index)
                )
                
                return df
            else:
                error_msg = "No trends data found in response"
                self._print(f"  Search failed: {error_msg}")
                self._log_api_search(
                    search_term=search_term,
                    time_range=time_range if time_range else "default",
                    api="searchapi",
                    granularity="D",
                    error=error_msg
                )
                return pd.DataFrame()
                
        except Exception as e:
            self._print(f"  Search failed: {str(e)}")
            self._log_api_search(
                search_term=search_term,
                time_range=time_range if time_range else "default",
                api="searchapi",
                granularity="D",
                error=str(e)
            )
            raise

    def save_to_csv(
        self,
        combined_df: pd.DataFrame,
        search_term: str,
        path: Optional[str] = None,
        comment: Optional[str] = None
    ) -> str:
        """Wrapper for module-level save_to_csv that uses instance verbose setting."""
        return save_to_csv(combined_df, search_term, path, comment, self.verbose)

    def _numbered_file_name(self, orig_name: str, n_digits: int = 3, path: Optional[str] = None) -> str:
        """Wrapper for module-level _numbered_file_name."""
        return _numbered_file_name(orig_name, n_digits, path)

    def _custom_mode(self, df: pd.DataFrame, axis: int = 1) -> pd.Series:
        """Wrapper for module-level _custom_mode."""
        return _custom_mode(df, axis)

    def _get_index_granularity(self, index: pd.DatetimeIndex) -> str:
        """Wrapper for module-level _get_index_granularity that uses instance verbose setting."""
        return _get_index_granularity(index, self.verbose)

    def _calculate_search_granularity(
        self,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime]
    ) -> Dict[str, Union[str, pd.DatetimeIndex]]:
        """Wrapper for module-level _calculate_search_granularity that uses instance verbose setting."""
        return _calculate_search_granularity(start_date, end_date, self.verbose)



# Example usage
if __name__ == "__main__":
    print("This is a library, not a script. It is used to do google trends searches easily.")
    