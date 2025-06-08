from typing import Dict, Union, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np
from .utils import load_config, _print_if_verbose, diff_hour, diff_day, diff_week, diff_month
import math

class GranularityConfig:
    """
    A class to manage granularity rules and calculate maximum records.
    
    This class provides access to granularity rules from the configuration
    and calculates maximum records for each granularity type.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the GranularityConfig with rules from config.
        
        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary containing granularity rules.
                If None, loads from default config.
        """
        if config is None:
            config = load_config()
            
        # Get granularity rules from config or use defaults
        default_rules = [
            {'name': 'hourly', 'max_days': 8, 'max_inclusive': True, 'code': 'h'},
            {'name': 'daily', 'max_days': 270, 'max_inclusive': True, 'code': 'D'},
            {'name': 'weekly', 'max_days': 1900, 'max_inclusive': True, 'code': 'W'},
            {'name': 'monthly', 'code': 'MS'}
        ]
        self.rules = config.get('granularity_rules', default_rules) if config else default_rules
        
        # Calculate max records for each granularity
        self._max_records = {}
        for rule in self.rules:
            if 'max_days' in rule:
                code = rule['code']
                max_days = rule['max_days']
                # If not inclusive, subtract 1 from max_days
                if not rule.get('max_inclusive', False):
                    max_days -= 1
                if code == 'h':
                    self._max_records[code] = max_days * 24
                elif code == 'D':
                    self._max_records[code] = max_days
                elif code == 'W':
                    self._max_records[code] = max_days // 7
            else:
                # Monthly has no limit, use infinity
                self._max_records[rule['code']] = float('inf')
    
    def get_max_records(self, granularity: Optional[str] = None) -> Union[int, Dict[str, Optional[int]]]:
        """
        Get the maximum number of records for a specific granularity or all granularities.
        
        Args:
            granularity (Optional[str]): The granularity code ('h', 'D', 'W', 'MS').
                If None, returns a dictionary of all granularities.
                
        Returns:
            Union[int, Dict[str, Optional[int]]]: Maximum records for the specified granularity
                or a dictionary of all granularities and their maximum records.
                
        Raises:
            ValueError: If an invalid granularity is specified.
        """
        if granularity is not None:
            if granularity not in self._max_records:
                raise ValueError(f"Invalid granularity: {granularity}")
            return self._max_records[granularity]
        return self._max_records.copy()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Update the configuration and recalculate maximum records.
        
        Args:
            config (Dict[str, Any]): New configuration dictionary containing granularity rules.
        """
        self.__init__(config)

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
    verbose: bool = False,
    granularity: Optional[str] = None
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
        granularity (Optional[str]): If provided, use this as the granularity instead of calculating it.
            Should be one of: 'h' (hourly), 'D' (daily), 'W' (weekly), 'MS' (month start)
        
    Returns:
        Dict[str, Union[str, pd.DatetimeIndex, pd.PeriodIndex, int]]: Dictionary containing:
            - "granularity": The appropriate granularity to use ("h" for hour, "D" for day, "W" for week, or "MS" for month start)
            - "datetime_index": A pandas DateTimeIndex with the appropriate frequency
            - "period_index": A pandas PeriodIndex with the appropriate frequency
            - "max_units": The maximum number of units possible for the calculated granularity
            - "blocks": Number of intervals needed to cover the full date range (1 if granularity not provided)
    """
    # Initialize GranularityConfig
    granularity_config = GranularityConfig(config)
    
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
    
    # Calculate total units in the date range
    if granularity is not None:
        granularity = granularity[0]
        # Get max_units for the provided granularity
        max_units = granularity_config.get_max_records(granularity)
        
        # Find the rule for this granularity
        rule = next((r for r in granularity_config.rules if r['code'][0] == granularity), None)
        if rule is None:
            raise ValueError(f"Invalid granularity: {granularity}")
            
        # Calculate total units based on the rule's code
        if rule['code'] == 'h':
            total_units = int((end_dt - start_dt).total_seconds() / 3600) + 1
        elif rule['code'] == 'D':
            total_units = (end_dt - start_dt).days + 1
        elif rule['code'] == 'W':
            total_units = ((end_dt - start_dt).days + 1) // 7 + 1
        elif rule['code'] == 'MS':
            total_units = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month) + 1
            
        # Calculate number of blocks needed, rounding up
        blocks = math.ceil(total_units / max_units)
    else:
        # Calculate the time range in days
        days_diff = (end_dt - start_dt).days
        
        # Determine granularity based on rules in order
        for rule in granularity_config.rules:
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
        blocks = 1  # Single block when granularity is calculated automatically
    
    # Create appropriate DateTimeIndex and PeriodIndex based on granularity
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
    
    _print_if_verbose(f"Datetime index length: {len(datetime_index)}", verbose)
    _print_if_verbose(f"Period index length: {len(period_index)}", verbose)
    
    if verbose:
        _print_if_verbose(f"Granularity for date range {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} ({days_diff} days) is {granularity}", verbose)
        _print_if_verbose(f"Created {len(datetime_index)} datetime periods and {len(period_index)} period indices", verbose)
        _print_if_verbose(f"Maximum units for {granularity} granularity: {max_units if max_units is not None else '[no limit]'}", verbose)
        _print_if_verbose(f"Number of blocks needed: {blocks}", verbose)
    
    return {
        "granularity": granularity,
        "datetime_index": datetime_index,
        "period_index": period_index,
        "max_units": max_units,
        "blocks": blocks
    } 