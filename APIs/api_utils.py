import time
import os
from datetime import datetime, timedelta
from typing import Optional, Callable, Union, Dict, Any, List, Tuple
import pandas as pd
import yaml
import unicodedata
import re
from types import SimpleNamespace
from dateutil.parser import parse, ParserError
from utils import load_config, _print_if_verbose
import numpy as np

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

def standardize_date_str(date_str: str, verbose: bool = False) -> Tuple[str, str, str]:
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
    original_date = clean_date_str

    first_date = None
    second_date = None
    first_date_dt = None
    second_date_dt = None
    first_incomplete = True
    second_incomplete = True
    # test for case like "2020-01-01 - 2020-01-07 or 2020-01-01 2020-01-07"
    if re.search(r'^\d{4}-\d{2}-\d{2}', clean_date_str):
        _print_if_verbose(f"Found ISO format date: {clean_date_str}", verbose)
        # extract the ISO format date
        first_date = re.search(r'^\d{4}-\d{2}-\d{2}', clean_date_str).group()
        first_date_dt = parse(first_date)
        # delete the first date from the string
        clean_date_str = clean_date_str.replace(first_date, '', 1).strip()
        # now see if there is another one
        if re.search(r'\d{4}-\d{2}-\d{2}', clean_date_str):
            second_date = re.search(r'\d{4}-\d{2}-\d{2}', clean_date_str).group()
            second_date_dt = parse(second_date)
            # delete the second date from the string
            clean_date_str = clean_date_str.replace(second_date, '', 1).strip()
    # test for case like "11/3/2021 - 11/10/2021"
    elif re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str):
        _print_if_verbose(f"Found MM/DD/YYYY format date: {clean_date_str}", verbose)
        first_date = re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str).group()
        first_date_dt = parse(first_date)
        # delete the first date from the string
        clean_date_str = clean_date_str.replace(first_date, '', 1).strip()
        # now see if there is another one
        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str):
            second_date = re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str).group()
            second_date_dt = parse(second_date)
            # delete the second date from the string
            clean_date_str = re.split(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str)[1].strip()
    # test for case like "Jan 1-7, 2020"
    elif re.search(r'\d+-\d+', clean_date_str):
        _print_if_verbose(f"Found DD-DD format date: {clean_date_str}", verbose)
        parts = re.split(r'\d+-\d+', clean_date_str)
        splitter = re.search(r'\d+-\d+', clean_date_str).group()
        front_digits = re.search(r'\d+', splitter).group()
        back_digits = re.search(r'-\d+', splitter).group().lstrip('-')
        back_year = re.search(r'\d+$', parts[1]).group()
        first_date = parts[0] + front_digits + ', ' + back_year
        second_date = back_digits + parts[1]
        # still gonna need to clean it if it's like "Jan 1-7" because first and second won't be complete dates
    # test for case like "Jan 1 - 7, 2020"
    elif re.search(r'\d+\s*-\s*\d+', clean_date_str):
        _print_if_verbose(f"Found DD - DD format date: {clean_date_str}", verbose)
        parts = re.split(r'\d+\s*-\s*\d+', clean_date_str)
        splitter = re.search(r'\d+\s*-\s*\d+', clean_date_str).group()
        front_digits = re.search(r'\d+', splitter).group()
        back_digits = re.search(r'-\s*\d+', splitter).group().lstrip('-')
        back_year = re.search(r'\d+$', parts[1]).group()
        first_date = parts[0] + front_digits + ', ' + back_year
        second_date = back_digits + parts[1]
        _print_if_verbose(parts, verbose)
        _print_if_verbose(splitter, verbose)
        _print_if_verbose(front_digits, verbose)
        _print_if_verbose(back_digits, verbose)
        _print_if_verbose(back_year, verbose)
        _print_if_verbose(first_date, verbose)
        _print_if_verbose(second_date, verbose)
    # test for case like "Jan 1-Dec 7, 2020"
    elif re.search(r'\d+-[a-zA-Z]+', clean_date_str):
        _print_if_verbose(f"Found DD-MM format date: {clean_date_str}", verbose)
        parts = re.split(r'\d+-[a-zA-Z]+', clean_date_str)
        splitter = re.search(r'\d+-[a-zA-Z]+', clean_date_str).group()
        front_digits = re.search(r'\d+', splitter).group()
        back_letters = re.search(r'-[a-zA-Z]+', splitter).group().lstrip('-')
        back_year = re.search(r'\d+$', parts[1]).group()
        first_date = parts[0] + front_digits + ', ' + back_year
        second_date = back_letters + parts[1]
    # search for case like "Jan 1 - Dec 7, 2020"
    elif re.search(r'\d+\s*-\s*[a-zA-Z]+', clean_date_str):
        _print_if_verbose(f"Found DD - MM format date: {clean_date_str}", verbose)
        parts = re.split(r'\d+\s*-\s*[a-zA-Z]+', clean_date_str)
        splitter = re.search(r'\d+\s*-\s*[a-zA-Z]+', clean_date_str).group()
        front_digits = re.search(r'\d+', splitter).group()
        back_letters = re.search(r'-\s*[a-zA-Z]+', splitter).group().lstrip('-').strip()
        back_year = re.search(r'\d+$', parts[1]).group()
        first_date = parts[0] + front_digits + ', ' + back_year
        second_date = back_letters + parts[1]
    # if we get here we can assume there's only one date.
    else:
        _print_if_verbose(f"Found single date: {clean_date_str}", verbose)
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
                "original_date": original_date,
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
            "original_date": original_date,
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
        "original_date": original_date,
        "first_date": first_date,
        "second_date": second_date,
        "first_date_dt": first_date_dt,
        "second_date_dt": second_date_dt,
        "first_incomplete": first_incomplete,
        "second_incomplete": second_incomplete,
        "formatted_range": formatted_range
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

def sinc_data(num_zero_crossings: int, max_value: float, min_value: float, num_points: int) -> np.ndarray:
    """
    Generate a sinc-like signal with specified parameters.
    
    Args:
        num_zero_crossings (int): Number of zero crossings on the positive axis only
        max_value (float): Maximum value of the signal
        min_value (float): Minimum value of the signal (will be at the edges)
        num_points (int): Number of points in the output array
        
    Returns:
        np.ndarray: Array of values following a sinc-like pattern
        
    Example:
        >>> data = sinc_data(2, 1.0, 0.0, 100)
        >>> # Returns array of length 100 with:
        >>> # - 2 zero crossings on positive axis
        >>> # - Maximum value of 1.0 at center
        >>> # - Minimum value of 0.0 at edges
    """
    # Create x values from -1 to 1
    x = np.linspace(-1, 1, num_points)
    
    # Scale x by number of zero crossings to fit more cycles
    x_scaled = x * num_zero_crossings
    
    # Generate sinc function
    # Add small epsilon to avoid division by zero
    epsilon = 1e-10
    y = np.sin(np.pi * x_scaled) / (np.pi * x_scaled + epsilon)
    
    # Scale to desired range
    # First scale to 0-1 range (except the first one)
    y = (y - -0.217233) / (y.max() - -0.217233) # this is always the global min value for the sinc function
    
    # Then scale to desired range
    y = y * (max_value - min_value) + min_value
    
    return y

if __name__ == "__main__":
    test_strings = [
        "2020-01-01 - 2020-01-07",
        "2020-01-01 2020-01-07",
        "2020-01-01 - 2020-01-07 or 2020-01-01 2020-01-07",
        "11/3/2021 - 11/10/2021",
        "Jan 1-7, 2020",
        "Jan 1 - 7, 2020",
        "Jan 1-Dec 7, 2020",
        "Jan 1 - Dec 7, 2020",
    ]
    for test_string in test_strings:
        print(f"Input: {test_string}")
        output = standardize_date_str(test_string, verbose=False)
        #print(output)
        print(f"Output: {output['formatted_range']['ymd']}")
