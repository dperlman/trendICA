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

def load_config() -> dict:
    """
    Load configuration from config.yaml if it exists and return it.
    If the file doesn't exist, copies default_config.yaml to config.yaml and loads from that.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    default_config_path = os.path.join(os.path.dirname(__file__), 'default_config.yaml')
    
    if not os.path.exists(config_path):
        if os.path.exists(default_config_path):
            import shutil
            shutil.copy2(default_config_path, config_path)
            print(f"Created config.yaml from default_config.yaml")
        else:
            print("Warning: Neither config.yaml nor default_config.yaml found")
            return {}
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def change_tor_identity(password: Optional[str], print_func: Optional[Callable] = None, control_port: Optional[int] = None) -> None:
    """
    Change the Tor identity by connecting to the Tor control port and sending a NEWNYM signal.
    Includes error handling and retry logic.
    
    Args:
        password (Optional[str]): Password for Tor control port
        print_func (Optional[Callable]): Function to use for printing debug information
        control_port (Optional[int]): Port number for Tor control port. If None, uses value from config.yaml
    """
    if print_func is None:
        print_func = print
        
    try:
        from stem.control import Controller
        from stem import Signal
    except ImportError:
        print_func("Error: stem library not installed. Please install it with 'pip install stem'")
        return
    
    if not password:
        print_func("Error: Tor control password not provided")
        return

    # Load control port from config if not provided
    if control_port is None:
        config = load_config()
        control_port = config.get('tor', {}).get('control_port', 9151)  # Default to 9151 if not found in config

    try:
        # Try to connect to the Tor control port
        with Controller.from_port(port=control_port) as controller:
            # Authenticate with the controller
            controller.authenticate(password=password)
            
            # Send the NEWNYM signal to change the identity
            controller.signal(Signal.NEWNYM)
            print_func("Tor identity changed successfully.")
            
            # Wait a moment to ensure the change takes effect
            time.sleep(2)
            
    except Exception as e:
        print_func(f"Error changing Tor identity: {e}")
        print_func("Make sure Tor is running with control port enabled.")
        print_func(f"Add 'ControlPort {control_port}' to your torrc file and restart Tor.")

def get_index_granularity(index: pd.DatetimeIndex, verbose: bool = False) -> str:
    """
    Determine the granularity of a pandas DateTimeIndex.
    
    Args:
        index (pd.DatetimeIndex): The DateTimeIndex to analyze
        verbose (bool): Whether to print debug information
        
    Returns:
        str: The granularity code ('h' for hour, 'D' for day, 'W' for week, 'ME' for month end)
    """
    # Handle empty DataFrame or non-DatetimeIndex
    if len(index) == 0 or not isinstance(index, pd.DatetimeIndex):
        return 'D'  # Default to daily granularity
        
    # First try to get the frequency directly
    if index.freq is not None:
        freq_str = str(index.freq)
        if 'h' in freq_str:
            return 'h'
        elif 'D' in freq_str:
            return 'D'
        elif 'W' in freq_str:
            return 'W'
        elif 'M' in freq_str or 'ME' in freq_str:
            return 'ME'
    
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
        {'name': 'hourly', 'max_days': 8, 'max_inclusive': True, 'code': 'h'},
        {'name': 'daily', 'max_days': 270, 'max_inclusive': True, 'code': 'D'},
        {'name': 'weekly', 'max_days': 1900, 'max_inclusive': True, 'code': 'W'},
        {'name': 'monthly', 'code': 'MS'}
    ]
    
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
    
    # Create DateTimeIndex with appropriate frequency, ensuring both start and end dates are included
    datetime_index = pd.date_range(start=start_dt, end=end_dt, freq=granularity, inclusive='both')
    
    # Create PeriodIndex with appropriate frequency
    period_index = pd.period_range(start=start_dt, end=end_dt, freq=granularity)
    
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

def _standardize_date_str(date_str: str, verbose: bool = False) -> Tuple[str, str, str]:
    """
    Get each date in a date range. We especially need to use this to standardize the date strings in the standardize_data output.
    
    Args:
        date_str (str): Date range string in format like "Dec 31, 2023 – Jan 6, 2024" or "Jan 7 – 13, 2024"
        
    Returns:
        Tuple[str, str, str]: The cleaned orignal date if applicable, start date, and end date. End date is None if no end date is provided
        
    Raises:
        ValueError: If the date string cannot be parsed
    """

    # First clean the unicode to ascii because serpapi returns some weird unicode characters
    clean_date_str = unicodedata.normalize('NFKC', date_str).strip()
    # now clean out any non-ascii characters
    if not clean_date_str.isascii():
        for char in clean_date_str:
            if char.isascii():
                pass
            else:
                _print_if_verbose(f"Found non-ascii character: {char.encode('unicode_escape').decode('ascii')}", verbose)
                _print_if_verbose(f"Fixable: \u2013\u2014\u2015\u2043\u2212\u23AF\u23E4\u2500\u2501\u2E3A\u2E3B\uFE58\uFE63\uFF0D replace with -", verbose)
        # replace various unicode dashes with ASCII hyphen
        clean_date_str = re.sub(r'[\u2013\u2014\u2015\u2043\u2212\u23AF\u23E4\u2500\u2501\u2E3A\u2E3B\uFE58\uFE63\uFF0D]', '-', clean_date_str)
        # we can fix more here if we ever learn others that need to be fixed.

    first_date = None
    second_date = None
    first_date_dt = None
    second_date_dt = None
    first_incomplete = True
    second_incomplete = True
    # test for case like "2020-01-01 - 2020-01-07 or 2020-01-01 2020-01-07"
    if re.search(r'^\d{4}-\d{2}-\d{2}', clean_date_str):
        # extract the ISO format date
        first_date = re.search(r'^\d{4}-\d{2}-\d{2}', clean_date_str).group()
        first_date_dt = parse(first_date)
        # delete the first date from the string
        clean_date_str = re.split(r'^\d{4}-\d{2}-\d{2}', clean_date_str)[1].strip()
        # now see if there is another one
        if re.search(r'\d{4}-\d{2}-\d{2}', clean_date_str):
            second_date = re.search(r'\d{4}-\d{2}-\d{2}', clean_date_str).group()
            second_date_dt = parse(second_date)
            # delete the second date from the string
            clean_date_str = re.split(r'^\d{4}-\d{2}-\d{2}', clean_date_str)[1].strip()
    # test for case like "11/3/2021 - 11/10/2021"
    elif re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str):
        first_date = re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str).group()
        first_date_dt = parse(first_date)
        # delete the first date from the string
        clean_date_str = re.split(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str)[1].strip()
        # now see if there is another one
        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str):
            second_date = re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str).group()
            second_date_dt = parse(second_date)
            # delete the second date from the string
            clean_date_str = re.split(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str)[1].strip()
    # test for case like "Jan 1-7, 2020"
    elif re.search(r'\d+-\d+', clean_date_str):
        parts = re.split(r'\d+-\d+', clean_date_str)
        splitter = re.search(r'\d+-\d+', clean_date_str).group()
        front_digits = re.search(r'\d+', splitter).group()
        back_digits = re.search(r'-\d+', splitter).group().lstrip('-')
        first_date = parts[0] + front_digits
        second_date = back_digits + parts[1]
        # still gonna need to clean it if it's like "Jan 1-7" because first and second won't be complete dates
    # test for case like "Jan 1 - 7, 2020"
    elif re.search(r'\d+\s*-\s*\d+', clean_date_str):
        parts = re.split(r'\d+\s*-\s*\d+', clean_date_str)
        splitter = re.search(r'\d+\s*-\s*\d+', clean_date_str).group()
        front_digits = re.search(r'\d+', splitter).group()
        back_digits = re.search(r'-\d+', splitter).group().lstrip('-')
        first_date = parts[0] + front_digits
        second_date = back_digits + parts[1]
    # test for case like "Jan 1-Dec 7, 2020"
    elif re.search(r'\d+-[a-zA-Z]+', clean_date_str):
        parts = re.split(r'\d+-[a-zA-Z]+', clean_date_str)
        splitter = re.search(r'\d+-[a-zA-Z]+', clean_date_str).group()
        front_digits = re.search(r'\d+', splitter).group()
        back_digits = re.search(r'-[a-zA-Z]+', splitter).group().lstrip('-')
        first_date = parts[0] + front_digits
        second_date = back_digits + parts[1]
    # search for case like "Jan 1 - Dec 7, 2020"
    elif re.match(r'\d+\s*-\s*[a-zA-Z]+ \d+$', clean_date_str):
        parts = re.split(r'\d+\s*-\s*[a-zA-Z]+ \d+$', clean_date_str)
        splitter = re.search(r'\d+\s*-\s*[a-zA-Z]+ \d+$', clean_date_str).group()
        front_digits = re.search(r'\d+', splitter).group()
        back_digits = re.search(r'-\s*[a-zA-Z]+', splitter).group().lstrip('-').strip()
        first_date = parts[0] + front_digits
        second_date = back_digits + parts[1]
    # if we get here we can assume there's only one date.
    else:
        try:
            first_date = clean_date_str
            first_date_dt = parse(clean_date_str)
        except (ValueError, ParserError):
            _print_if_verbose(f"Could not parse date string: {clean_date_str}", verbose)
            first_date = None
            second_date = None
            first_date_dt = None
            second_date_dt = None
            return {
                "original_date": clean_date_str,
                "first_date": None,
                "second_date": None,
                "first_date_dt": None,
                "second_date_dt": None,
                "first_incomplete": False,
                "second_incomplete": True,
                "formatted_range": None
            }
    # this is good enough. Probably total overkill. If we get here, we either have one date or we have two (partial)dates.
    if first_date and not second_date: # easy, if there's only one date, we're done.
        return {
            "original_date": clean_date_str,
            "first_date": first_date,
            "second_date": None,
            "first_date_dt": first_date_dt,
            "second_date_dt": None,
            "first_incomplete": False,
            "second_incomplete": True,
            "formatted_range": first_date_dt.strftime("%Y-%m-%d")
        }
    # now we come to the annoying part. we have two partial dates and we have to sort that out.

    if first_date:
        try:
            first_date_dt = parse(first_date)
            first_incomplete = False
        except (ParserError):
            pass
    if second_date:
        try:
            second_date_dt = parse(second_date)
            second_incomplete = False
        except (ParserError):
            pass
    # now we have to sort out the partial dates.
    if first_incomplete:
        # for now assume it looks like "Jan 1" or "January 1"
        # and assume the 4-digit year is at the end of the second string
        date_year = re.search(r'\d{4}\s*$', second_date).group()
        first_date = first_date + ', ' + date_year
        try:
            first_date_dt = parse(first_date)
            first_incomplete = False
        except (ParserError):
            pass
    if second_incomplete:
        # for now assume it looks like "3, 2024"
        # and assume the month is at the beginning of the first string
        date_month = re.search(r'[a-zA-Z]{2,}', first_date).group()
        # yes I know this is totally not locale safe. Someone can add that later maybe.
        second_date = date_month + ' ' + second_date
        try:
            second_date_dt = parse(second_date)
            second_incomplete = False
        except (ParserError):
            pass
    # now we have pretty much done all we can do, except locale stuff which I am not going to do now.
    # so we will return what we have.
    try:
        formatted_range = make_time_range(first_date_dt, second_date_dt)
    except:
        try:
            formatted_range = first_date_dt.strftime("%Y-%m-%d")
        except:
            formatted_range = None
    return {
        "original_date": clean_date_str,
        "first_date": first_date,
        "second_date": second_date,
        "first_date_dt": first_date_dt,
        "second_date_dt": second_date_dt,
        "first_incomplete": first_incomplete,
        "second_incomplete": second_incomplete,
        "formatted_range": formatted_range
    }

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
        
        # Initialize the last caller attribute if it doesn't exist
        if not hasattr(_print_if_verbose, 'last_caller'):
            _print_if_verbose.last_caller = None
        
        # Get the caller's frame info
        caller = inspect.currentframe().f_back
        # Get the caller's function name
        caller_name = caller.f_code.co_name
        
        # If the caller is _print, get the caller of _print instead
        if caller_name == '_print':
            caller = caller.f_back
            caller_name = caller.f_code.co_name
        
        # Only print the caller name if it has changed
        if caller_name != _print_if_verbose.last_caller:
            print(f"\n[{caller_name}]")
            _print_if_verbose.last_caller = caller_name
            
        # Print the message
        print(message)

def make_time_range(
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None
) -> SimpleNamespace:
    """
    Convert start_date and end_date into a formatted time range string.
    If dates are strings, they will be parsed into datetime objects.
    If no dates are provided, defaults to the last 270 days.
    The output format will be "YYYY-MM-DD YYYY-MM-DD".
    
    Args:
        start_date (Optional[Union[str, datetime]]): Start date. If string, will be parsed with dateutil.parser
        end_date (Optional[Union[str, datetime]]): End date. If string, will be parsed with dateutil.parser
        
    Returns:
        SimpleNamespace: Object containing:
            - ymd: Time range string in format "YYYY-MM-DD YYYY-MM-DD"
            - mdy: Time range string in format "MM/DD/YYYY MM/DD/YYYY"
            - start_datetime: Start date as datetime object
            - end_datetime: End date as datetime object
    """
    # If no dates provided, default to last 270 days
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=270)

    # default datetime object for parser is january 1 of this year and has hour zero
    default_datetime = datetime(2025, 1, 1, 0, 0, 0)

    # Parse string dates into datetime objects
    if isinstance(start_date, str):
        start_date = parse(start_date, default=default_datetime)
    if isinstance(end_date, str):
        end_date = parse(end_date, default=default_datetime)
        
    # Format dates as YYYY-MM-DD
    start_str_ymd = start_date.strftime("%Y-%m-%d") if start_date else ""
    end_str_ymd = end_date.strftime("%Y-%m-%d") if end_date else ""
    
    # Format dates as MM/DD/YYYY
    start_str_mdy = start_date.strftime("%m/%d/%Y") if start_date else ""
    end_str_mdy = end_date.strftime("%m/%d/%Y") if end_date else ""
    
    # Combine into time range strings
    time_range_ymd = f"{start_str_ymd} {end_str_ymd}".strip()
    time_range_mdy = f"{start_str_mdy} {end_str_mdy}".strip()
    
    return {
        "ymd": time_range_ymd,
        "mdy": time_range_mdy,
        "start_datetime": start_date,
        "end_datetime": end_date
    }

def standard_dict_to_df(standardized_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert standardized dictionary format to a pandas DataFrame.
    
    Args:
        standardized_data (List[Dict[str, Any]]): List of dictionaries in standardized format,
            where each dict has 'date' and 'values' keys. The 'values' key contains a list of
            dicts with 'query' and 'value' keys.
            
    Returns:
        pd.DataFrame: DataFrame with dates as PeriodIndex and one column per search term.
            Column names are sanitized versions of the search terms.
    """
    # Create a dictionary to store the data
    data_dict = {}
    
    # Process each entry in the standardized data
    for entry in standardized_data:
        date = entry['date']
        for value_dict in entry['values']:
            query = value_dict['query']
            value = value_dict['value']
            
            # Sanitize the query name for use as a column name
            sanitized_query = query.replace(' ', '_').lower()
            
            # Add the value to the data dictionary
            if sanitized_query not in data_dict:
                data_dict[sanitized_query] = {}
            data_dict[sanitized_query][date] = value
    
    # Create DataFrame from the dictionary
    df = pd.DataFrame(data_dict)
    
    # Convert index to datetime first, then to period
    df.index = pd.to_datetime(df.index)
    
    # Determine the appropriate frequency for the PeriodIndex
    # Get the time differences between consecutive dates
    time_diffs = df.index.to_series().diff()
    
    # If all differences are 1 day, use daily frequency
    if (time_diffs == pd.Timedelta(days=1)).all():
        freq = 'D'
    # If all differences are 1 week, use weekly frequency
    elif (time_diffs == pd.Timedelta(weeks=1)).all():
        freq = 'W'
    # If all dates are the first of the month, use monthly frequency
    elif (df.index.day == 1).all():
        freq = 'MS'
    # If all differences are 1 hour, use hourly frequency
    elif (time_diffs == pd.Timedelta(hours=1)).all():
        freq = 'h'
    else:
        # Default to daily frequency if we can't determine
        freq = 'D'
    
    # Convert to PeriodIndex
    df.index = df.index.to_period(freq)
    
    # Sort by date
    df = df.sort_index()
    
    return df
