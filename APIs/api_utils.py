import time
import os
from datetime import datetime, timedelta
from typing import Optional, Callable, Union, Dict, Any, List
import pandas as pd
import yaml
from types import SimpleNamespace
from dateutil import parser
from utils import load_config

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
        start_date = parser.parse(start_date, default=default_datetime)
    if isinstance(end_date, str):
        end_date = parser.parse(end_date, default=default_datetime)
        
    # Format dates as YYYY-MM-DD
    start_str_ymd = start_date.strftime("%Y-%m-%d") if start_date else ""
    end_str_ymd = end_date.strftime("%Y-%m-%d") if end_date else ""
    
    # Format dates as MM/DD/YYYY
    start_str_mdy = start_date.strftime("%m/%d/%Y") if start_date else ""
    end_str_mdy = end_date.strftime("%m/%d/%Y") if end_date else ""
    
    # Combine into time range strings
    time_range_ymd = f"{start_str_ymd} {end_str_ymd}".strip()
    time_range_mdy = f"{start_str_mdy} {end_str_mdy}".strip()
    
    return SimpleNamespace(
        ymd=time_range_ymd,
        mdy=time_range_mdy,
        start_datetime=start_date,
        end_datetime=end_date
    )

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

