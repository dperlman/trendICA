import time
import os
import re
import sys
import unicodedata
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Callable, Union, Dict, Tuple, Any, List
import yaml
from dateutil.parser import parse, ParserError
from types import SimpleNamespace
import appdirs
import shutil

def load_config() -> dict:
    """
    Load configuration from config.yaml if it exists and return it.
    If the file doesn't exist, copies default_config.yaml to config.yaml and loads from that.
    Also loads granularity_rules.yaml from the package config folder.
    
    Config file locations (in order of precedence):
    1. Local config: ./config.yaml (for development)
    2. User config: ~/.config/gtrend_api_tools/config.yaml (for installed package)
    3. Package default: gtrend_api_tools/config/default_config.yaml
    
    Granularity rules are loaded from:
    - gtrend_api_tools/config/granularity_rules.yaml
    
    The granularity rules in the config are sorted by max_days in ascending order.
    Rules with max_days=None are placed at the end.
    """
    # First check for local config.yaml (development mode)
    local_config_path = os.path.join(os.getcwd(), 'config.yaml')
    if os.path.exists(local_config_path):
        with open(local_config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        # Get user config directory
        config_dir = appdirs.user_config_dir('gtrend_api_tools')
        user_config_path = os.path.join(config_dir, 'config.yaml')
        
        # Package default config path
        package_config_path = os.path.join(os.path.dirname(__file__), 'config', 'default_config.yaml')
        
        # Create user config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # If user config doesn't exist, copy from package default
        if not os.path.exists(user_config_path):
            if os.path.exists(package_config_path):
                shutil.copy2(package_config_path, user_config_path)
                print(f"Created user config at {user_config_path}")
            else:
                print("Warning: Default config file not found in package")
                return {}
        
        # Load user config
        with open(user_config_path, 'r') as f:
            config = yaml.safe_load(f)
    
    # Load granularity rules from package config
    package_rules_path = os.path.join(os.path.dirname(__file__), 'config', 'granularity_rules.yaml')
    if os.path.exists(package_rules_path):
        with open(package_rules_path, 'r') as f:
            rules_config = yaml.safe_load(f)
            if rules_config and 'granularity_rules' in rules_config:
                config['granularity_rules'] = rules_config['granularity_rules']
    
    # Sort granularity rules by max_days
    if 'granularity_rules' in config:
        rules = config['granularity_rules']
        # Convert to list of tuples (code, rule) for sorting
        rule_items = list(rules.items())
        # Sort by max_days, putting None values at the end
        rule_items.sort(key=lambda x: (x[1].get('max_days') is None, x[1].get('max_days', float('inf'))))
        # Convert back to dict
        config['granularity_rules'] = dict(rule_items)
    
    return config


# def change_tor_identity(password: Optional[str], print_func: Optional[Callable] = None, control_port: Optional[int] = None) -> None:
#     """
#     Change the Tor identity by connecting to the Tor control port and sending a NEWNYM signal.
#     Includes error handling and retry logic.
    
#     Args:
#         password (Optional[str]): Password for Tor control port
#         print_func (Optional[Callable]): Function to use for printing debug information
#         control_port (Optional[int]): Port number for Tor control port. If None, uses value from config.yaml
#     """
#     if print_func is None:
#         print_func = print
        
#     try:
#         from stem.control import Controller
#         from stem import Signal
#     except ImportError:
#         print_func("Error: stem library not installed. Please install it with 'pip install stem'")
#         return
    
#     if not password:
#         print_func("Error: Tor control password not provided")
#         return

#     # Load control port from config if not provided
#     if control_port is None:
#         config = load_config()
#         control_port = config.get('tor', {}).get('control_port', 9151)  # Default to 9151 if not found in config

#     try:
#         # Try to connect to the Tor control port
#         with Controller.from_port(port=control_port) as controller:
#             # Authenticate with the controller
#             controller.authenticate(password=password)
            
#             # Send the NEWNYM signal to change the identity
#             controller.signal(Signal.NEWNYM)
#             print_func("Tor identity changed successfully.")
            
#             # Wait a moment to ensure the change takes effect
#             time.sleep(2)
            
#     except Exception as e:
#         print_func(f"Error changing Tor identity: {e}")
#         print_func("Make sure Tor is running with control port enabled.")
#         print_func(f"Add 'ControlPort {control_port}' to your torrc file and restart Tor.")

def get_index_granularity(index: Union[pd.DatetimeIndex, pd.PeriodIndex], verbose: bool = False) -> str:
    """
    Determine the granularity of a pandas DateTimeIndex or PeriodIndex.
    
    Args:
        index (Union[pd.DatetimeIndex, pd.PeriodIndex]): The index to analyze
        verbose (bool): Whether to print debug information
        
    Returns:
        str: The granularity code ('h' for hour, 'D' for day, 'W' for week, 'ME' for month end)
    """
    # Handle empty DataFrame or invalid index type
    if len(index) == 0 or not isinstance(index, (pd.DatetimeIndex, pd.PeriodIndex)):
        return 'D'  # Default to daily granularity
        
    # First try to get the frequency directly
    if index.freq is not None:
        freq_str = str(index.freq)
        if freq_str.startswith('h'):
            return 'h'
        elif freq_str.startswith('D'):
            return 'D'
        elif freq_str.startswith('W'):
            return 'W'
        elif freq_str.startswith('M'):
            return 'M'
    # If no frequency is set, try to infer from time differences
    if len(index) < 2:
        return 'D'  # Default to day if we can't determine
    
    # Convert PeriodIndex to DatetimeIndex if needed
    if isinstance(index, pd.PeriodIndex):
        index = index.to_timestamp()
    
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
        return 'h'
    elif td <= pd.Timedelta(days=1):
        return 'D'
    elif td <= pd.Timedelta(weeks=1):
        return 'W'
    else:
        return 'ME'

def calculate_search_granularity(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    config: Optional[Dict[str, Any]] = None,
    verbose: bool = False
) -> Dict[str, Union[str, pd.DatetimeIndex, pd.PeriodIndex, int]]:
    """
    Calculate the appropriate granularity for a Google Trends search based on the time range
    and generate the corresponding DateTimeIndex and PeriodIndex.

    This takes start_date and end_date, truncates any HH:MM:SS, and then calculates the granularity based on the time range.

    Note: Although Google Trends allows (secretly, behind the scenes) for dates to be specified with hours for very short time ranges,
    we don't use this because it's not documented and it's not clear if it's reliable. We had to draw the line somewhere.
    
    Args:
        start_date (Union[str, datetime]): Start date of the search
        end_date (Union[str, datetime]): End date of the search
        config (Optional[Dict[str, Any]]): Configuration dictionary containing granularity rules
        verbose (bool): Whether to print debug information
        
    Returns:
        Dict[str, Union[str, pd.DatetimeIndex, pd.PeriodIndex, int]]: Dictionary containing:
            - "granularity": The appropriate granularity to use ("h" for hour, "D" for day, "W" for week, or "MS" for month start)
            - "datetime_index": A pandas DateTimeIndex with the appropriate frequency
            - "period_index": A pandas PeriodIndex with the appropriate frequency
            - "max_units": The maximum number of units possible for the calculated granularity
    """
    # Get granularity rules from config or use defaults
    default_rules = [
        {'name': 'hourly', 'max_days': 8, 'max_inclusive': False, 'code': 'h'},
        {'name': 'daily', 'max_days': 270, 'max_inclusive': False, 'code': 'D'},
        {'name': 'weekly', 'max_days': 1900, 'max_inclusive': False, 'code': 'W'},
        {'name': 'monthly', 'code': 'MS'}
    ]
    
    # Load config if not provided
    if config is None:
        config = load_config()
    verbose = True
    # Get granularity rules from config or use defaults
    granularity_rules = config.get('granularity_rules', default_rules) if config else default_rules
    
    # Convert dates to datetime if they're strings
    if isinstance(start_date, str):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = start_date
        
    if isinstance(end_date, str):
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = end_date
    
    # Truncate any HH:MM:SS
    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate the time range in days
    days_diff = (end_dt - start_dt).days
    
    # Determine granularity based on rules in order
    for rule in granularity_rules:
        if 'max_days' in rule:
            if rule['max_inclusive']:
                if days_diff <= rule['max_days']:
                    granularity = rule['code']
                    max_units = rule['max_days']
                    break
            else:
                if days_diff < rule['max_days']:
                    granularity = rule['code']
                    max_units = rule['max_days']
                    break
        else:
            # Last rule (monthly) has no max_days
            granularity = rule['code']
            max_units = None  # No limit for monthly
            break
    
    # if granularity is monthly, we need to calculate the number of months between start and end dates
    # first replace the day of the month with the first day of the month

    
    if granularity == 'h':
        hour_diff = diff_hour(start_dt, end_dt)
        _print_if_verbose(f"Hours difference: {hour_diff}", verbose)
        datetime_index = pd.date_range(start=start_dt, freq=granularity, periods=hour_diff + 1)
        period_index = pd.PeriodIndex(datetime_index)
    elif granularity == 'D':
        days_diff = diff_day(start_dt, end_dt)
        _print_if_verbose(f"Days difference: {days_diff}", verbose)
        datetime_index = pd.date_range(start=start_dt, freq=granularity, periods=days_diff + 1)
        period_index = pd.PeriodIndex(datetime_index)
    elif granularity == 'W':
        weeks_diff = diff_week(start_dt, end_dt)
        _print_if_verbose(f"Weeks difference: {weeks_diff}", verbose)
        datetime_index = pd.date_range(start=start_dt, freq=granularity, periods=weeks_diff + 1)
        period_index = pd.PeriodIndex(datetime_index)
    elif granularity == 'MS':
        months_diff = diff_month(start_dt, end_dt)
        _print_if_verbose(f"Months difference: {months_diff}", verbose)
        datetime_index = pd.date_range(start=start_dt.replace(day=1), freq=granularity, periods=months_diff + 1)
        period_index = pd.PeriodIndex(datetime_index, freq='M')
    # Create DateTimeIndex with appropriate frequency, ensuring both start and end dates are included
    #datetime_index = pd.date_range(start=start_dt, freq=granularity, periods=days_diff + 1)
    _print_if_verbose(f"Datetime index length: {len(datetime_index)}", verbose)
    _print_if_verbose(f"Period index length: {len(period_index)}", verbose)
    
    # Create PeriodIndex with appropriate frequency
    #period_index = pd.period_range(start=start_dt, end=end_dt, freq=granularity)
    
    if verbose:
        _print_if_verbose(f"Granularity for date range {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} ({days_diff} days) is {granularity}", verbose)
        _print_if_verbose(f"Created {len(datetime_index)} datetime periods and {len(period_index)} period indices", verbose)
        _print_if_verbose(f"Maximum units for {granularity} granularity: {max_units if max_units is not None else '[no limit]'}", verbose)
    
    return {
        "granularity": granularity,
        "datetime_index": datetime_index,
        "period_index": period_index,
        "max_units": max_units
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
    
    if path:
        new_name = os.path.join(path, new_name)
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
    
    # _numbered_file_name will handle the path if provided
    
    # First write the comment if provided
    if comment:
        with open(filename, 'w') as f:
            f.write(f"# {comment}\n")
    
    # Save the dataframe to the CSV file
    combined_df.to_csv(filename, index=True, mode='a')
    _print_if_verbose(f"\nData saved to {filename}", verbose)
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

def _print_if_verbose(message: str, verbose: bool = False) -> None:
    """
    Print message only if verbose is True, prefixed with the caller's function name and its caller.
    If the caller is _print, uses the caller of _print instead.
    Only prints the caller names if they have changed from the last call.
    
    Args:
        message (str): The message to print
        verbose (bool): Whether to print the message
    """
    if verbose:
        import inspect
        
        # Initialize the last caller attributes if they don't exist
        if not hasattr(_print_if_verbose, 'last_caller'):
            _print_if_verbose.last_caller = None
        if not hasattr(_print_if_verbose, 'last_caller_caller'):
            _print_if_verbose.last_caller_caller = None
        
        # Get the caller's frame info
        caller = inspect.currentframe().f_back
        # Get the caller's function name
        caller_name = caller.f_code.co_name
        
        # If the caller is _print, get the caller of _print instead
        if caller_name == '_print':
            caller = caller.f_back
            caller_name = caller.f_code.co_name
        
        # Get the caller's caller
        caller_caller = caller.f_back
        caller_caller_name = caller_caller.f_code.co_name if caller_caller else "unknown"
        
        # Only print the caller names if they have changed
        if caller_name != _print_if_verbose.last_caller or caller_caller_name != _print_if_verbose.last_caller_caller:
            print(f"\n[{caller_caller_name}] / [{caller_name}]")
            _print_if_verbose.last_caller = caller_name
            _print_if_verbose.last_caller_caller = caller_caller_name
            
        # Print the message
        print(message)

def diff_month(d1: datetime, d2: datetime) -> int:
    d2m = d2.replace(day=1) # replace the day of the month with the first day of the month
    d1m = d1.replace(day=1) # replace the day of the month with the first day of the month
    return (d2m.year - d1m.year) * 12 + d2m.month - d1m.month

def diff_week(d1: datetime, d2: datetime) -> int:
    return ((d2-d1).days // 7) # need to test to see if this is correct

def diff_day(d1: datetime, d2: datetime) -> int:
    return (d2-d1).days

def diff_hour(d1: datetime, d2: datetime) -> int:
    return (d2-d1).seconds // 3600


# def make_time_range(
#     start_date: Optional[Union[str, datetime]] = None,
#     end_date: Optional[Union[str, datetime]] = None
# ) -> SimpleNamespace:
#     """
#     Convert start_date and end_date into a formatted time range string.
#     If dates are strings, they will be parsed into datetime objects.
#     If no dates are provided, defaults to the last 270 days.
#     The output format will be "YYYY-MM-DD YYYY-MM-DD".
    
#     Args:
#         start_date (Optional[Union[str, datetime]]): Start date. If string, will be parsed with dateutil.parser
#         end_date (Optional[Union[str, datetime]]): End date. If string, will be parsed with dateutil.parser
        
#     Returns:
#         SimpleNamespace: Object containing:
#             - ymd: Time range string in format "YYYY-MM-DD YYYY-MM-DD"
#             - mdy: Time range string in format "MM/DD/YYYY MM/DD/YYYY"
#             - start_datetime: Start date as datetime object
#             - end_datetime: End date as datetime object
#     """
#     # If no dates provided, default to last 270 days
#     if not start_date and not end_date:
#         end_date = datetime.now()
#         start_date = end_date - timedelta(days=270)

#     # default datetime object for parser is january 1 of this year and has hour zero
#     default_datetime = datetime(2025, 1, 1, 0, 0, 0)

#     # Parse string dates into datetime objects
#     if isinstance(start_date, str):
#         start_date = parse(start_date, default=default_datetime)
#     if isinstance(end_date, str):
#         end_date = parse(end_date, default=default_datetime)
        
#     # Format dates as YYYY-MM-DD
#     start_str_ymd = start_date.strftime("%Y-%m-%d") if start_date else ""
#     end_str_ymd = end_date.strftime("%Y-%m-%d") if end_date else ""
    
#     # Format dates as MM/DD/YYYY
#     start_str_mdy = start_date.strftime("%m/%d/%Y") if start_date else ""
#     end_str_mdy = end_date.strftime("%m/%d/%Y") if end_date else ""
    
#     # Combine into time range strings
#     time_range_ymd = f"{start_str_ymd} {end_str_ymd}".strip()
#     time_range_mdy = f"{start_str_mdy} {end_str_mdy}".strip()
    
#     return {
#         "ymd": time_range_ymd,
#         "mdy": time_range_mdy,
#         "start_datetime": start_date,
#         "end_datetime": end_date
#     }

# def standard_dict_to_df(standardized_data: List[Dict[str, Any]]) -> pd.DataFrame:
#     """
#     Convert standardized dictionary format to a pandas DataFrame.
    
#     Args:
#         standardized_data (List[Dict[str, Any]]): List of dictionaries in standardized format,
#             where each dict has 'date' and 'values' keys. The 'values' key contains a list of
#             dicts with 'query' and 'value' keys.
            
#     Returns:
#         pd.DataFrame: DataFrame with dates as PeriodIndex and one column per search term.
#             Column names are sanitized versions of the search terms.
#     """
#     # Create a dictionary to store the data
#     data_dict = {}
    
#     # Process each entry in the standardized data
#     for entry in standardized_data:
#         date = entry['date']
#         for value_dict in entry['values']:
#             query = value_dict['query']
#             value = value_dict['value']
            
#             # Sanitize the query name for use as a column name
#             sanitized_query = query.replace(' ', '_').lower()
            
#             # Add the value to the data dictionary
#             if sanitized_query not in data_dict:
#                 data_dict[sanitized_query] = {}
#             data_dict[sanitized_query][date] = value
    
#     # Create DataFrame from the dictionary
#     df = pd.DataFrame(data_dict)
    
#     # Convert index to datetime first, then to period
#     df.index = pd.to_datetime(df.index)
    
#     # Determine the appropriate frequency for the PeriodIndex
#     # Get the time differences between consecutive dates
#     time_diffs = df.index.to_series().diff()
    
#     # If all differences are 1 day, use daily frequency
#     if (time_diffs == pd.Timedelta(days=1)).all():
#         freq = 'D'
#     # If all differences are 1 week, use weekly frequency
#     elif (time_diffs == pd.Timedelta(weeks=1)).all():
#         freq = 'W'
#     # If all dates are the first of the month, use monthly frequency
#     elif (df.index.day == 1).all():
#         freq = 'MS'
#     # If all differences are 1 hour, use hourly frequency
#     elif (time_diffs == pd.Timedelta(hours=1)).all():
#         freq = 'h'
#     else:
#         # Default to daily frequency if we can't determine
#         freq = 'D'
    
#     # Convert to PeriodIndex
#     df.index = df.index.to_period(freq)
    
#     # Sort by date
#     df = df.sort_index()
    
#     return df
