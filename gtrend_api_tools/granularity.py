from typing import Dict, Union, Optional, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from .utils import load_config, _print_if_verbose, diff_hour, diff_day, diff_week, diff_month
import math

class GranularityManager:
    """
    A class to manage granularity rules and calculations.
    
    This class provides functionality for:
    - Managing granularity rules from configuration
    - Determining granularity from time indices
    - Creating time indices
    - Calculating total units
    - Determining search granularity
    
    The rules are sorted by max_days in ascending order, with rules having
    max_days=None placed at the end.
    """
    def __init__(self, config: dict, verbose: bool = True):
        """
        Initialize granularity manager.
        
        Args:
            config (dict): Configuration dictionary containing granularity rules
            verbose (bool): Whether to print debug information. Defaults to False.
        """
        if not isinstance(config, dict):
            raise ValueError("config must be a dictionary")
        self.rules = config.get('granularity_rules', {})
        if not self.rules:
            raise ValueError("No granularity rules found in config")
        self.verbose = verbose

    def get_index_granularity(self, index: Union[pd.DatetimeIndex, pd.PeriodIndex]) -> str:
        """
        Determine the granularity of a pandas DateTimeIndex or PeriodIndex.
        
        Args:
            index (Union[pd.DatetimeIndex, pd.PeriodIndex]): The index to analyze
            
        Returns:
            str: The granularity code ('h' for hour, 'D' for day, 'W' for week, 'ME' for month end)
        """
        # Handle empty DataFrame or invalid index type
        if len(index) == 0 or not isinstance(index, (pd.DatetimeIndex, pd.PeriodIndex)):
            return None # it doesn't make sense to return a granularity code if we don't have any data
        if len(index) < 2:
            return None # it doesn't make sense to return a granularity code if there's only one data point
            
        # First try to get the frequency directly
        if index.freq is not None:
            freq_str = str(index.freqstr)[0]
            return freq_str
        
        # If no frequency is set, try to infer from time differences
        # Convert PeriodIndex to DatetimeIndex if needed
        if isinstance(index, pd.PeriodIndex):
            index = index.to_timestamp()
        
        # Calculate time differences in nanoseconds
        time_diffs = np.diff(index.astype(np.int64))
        
        # Print debugging information
        _print_if_verbose("Unique time differences and their counts:", self.verbose)
        _print_if_verbose(pd.Series(time_diffs).value_counts(), self.verbose)
        
        # Use pandas value_counts instead of np.bincount for memory efficiency
        most_common_diff = pd.Series(time_diffs).value_counts().index[0]
        _print_if_verbose(f"Most common difference: {most_common_diff} nanoseconds", self.verbose)
        
        # Convert to timedelta and check
        td = pd.Timedelta(most_common_diff, unit='ns')
        _print_if_verbose(f"Converted to timedelta: {td}", self.verbose)
        
        # Find the first rule where the time difference is less than or equal to record_seconds
        for code, rule in self.rules.items():
            if td.total_seconds() <= rule['record_seconds']:
                return code
        
        # If no rule matches, return monthly (last resort)
        return 'M'

    def create_time_indices(
        self,
        start_dt: datetime,
        end_dt: datetime,
        granularity: str
    ) -> Tuple[pd.DatetimeIndex, pd.PeriodIndex]:
        """
        Create DateTimeIndex and PeriodIndex based on the given date range and granularity.
        
        Args:
            start_dt (datetime): Start date
            end_dt (datetime): End date
            granularity (str): Time granularity code ('h', 'D', 'W', 'M')
            
        Returns:
            Tuple[pd.DatetimeIndex, pd.PeriodIndex]: A tuple containing the DateTimeIndex and PeriodIndex
            
        Raises:
            ValueError: If granularity is not one of 'h', 'D', 'W', 'M'
        """
        if granularity not in self.rules:
            raise ValueError(f"Invalid granularity: {granularity}. Must be one of: {list(self.rules.keys())}")
            
        if granularity == 'h':
            hour_diff = diff_hour(start_dt, end_dt)
            _print_if_verbose(f"Hours difference: {hour_diff}", self.verbose)
            datetime_index = pd.date_range(start=start_dt, freq=granularity, periods=hour_diff + 1)
            period_index = pd.PeriodIndex(datetime_index)
        elif granularity == 'D':
            days_diff = diff_day(start_dt, end_dt)
            _print_if_verbose(f"Days difference: {days_diff}", self.verbose)
            datetime_index = pd.date_range(start=start_dt, freq=granularity, periods=days_diff + 1)
            period_index = pd.PeriodIndex(datetime_index)
        elif granularity == 'W':
            weeks_diff = diff_week(start_dt, end_dt)
            _print_if_verbose(f"Weeks difference: {weeks_diff}", self.verbose)
            datetime_index = pd.date_range(start=start_dt, freq=granularity, periods=weeks_diff + 1)
            period_index = pd.PeriodIndex(datetime_index)
        elif granularity == 'M':
            months_diff = diff_month(start_dt, end_dt)
            _print_if_verbose(f"Months difference: {months_diff}", self.verbose)
            datetime_index = pd.date_range(start=start_dt.replace(day=1), freq='MS', periods=months_diff + 1)
            period_index = pd.PeriodIndex(datetime_index, freq='M')
        
        _print_if_verbose(f"Datetime index length: {len(datetime_index)}", self.verbose)
        _print_if_verbose(f"Period index length: {len(period_index)}", self.verbose)
        
        return datetime_index, period_index
    
    def calculate_total_units(
        self,
        start_dt: datetime,
        end_dt: datetime,
        granularity: str
    ) -> Dict[str, Union[int, pd.PeriodIndex]]:
        """
        Calculate the total number of time units between two dates for a given granularity.
        
        Args:
            start_dt (datetime): Start date
            end_dt (datetime): End date
            granularity (str): Time granularity code ('h', 'D', 'W', 'M')
            
        Returns:
            Dict[str, Union[int, pd.PeriodIndex]]: Dictionary containing:
                - num_periods: Total number of time units between the dates
                - period_index: The period index used for calculation
            
        Raises:
            ValueError: If granularity is not one of 'h', 'D', 'W', 'M'
        """
        if granularity not in self.rules:
            raise ValueError(f"Invalid granularity: {granularity}. Must be one of: {list(self.rules.keys())}")
            
        period_index = pd.period_range(start=start_dt, end=end_dt, freq=granularity)
        _print_if_verbose(f"Created period index with {len(period_index)} periods for granularity {granularity}", self.verbose)
        #_print_if_verbose(f"Period index: {period_index}", self.verbose)
        
        return {
            'num_periods': len(period_index),
            'period_index': period_index
        }

    def calculate_search_granularity(
        self,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
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
            granularity (Optional[str]): If provided, use this as the granularity instead of calculating it.
                Should be one of: 'h' (hourly), 'D' (daily), 'W' (weekly), 'M' (month start)
            
        Returns:
            Dict[str, Union[str, pd.DatetimeIndex, pd.PeriodIndex, int]]: Dictionary containing:
                - "granularity": The appropriate granularity to use ("h" for hour, "D" for day, "W" for week, or "M" for month start)
                - "datetime_index": A pandas DateTimeIndex with the appropriate frequency
                - "period_index": A pandas PeriodIndex with the appropriate frequency
                - "max_units": The maximum number of units possible for the calculated granularity
                - "blocks": Number of intervals needed to cover the full date range (1 if granularity not provided)
        """
        # Convert dates to datetime if they're strings
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            _print_if_verbose(f"Converted start_date string to datetime: {start_dt}", self.verbose)
        else:
            start_dt = start_date
            
        if isinstance(end_date, str):
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            _print_if_verbose(f"Converted end_date string to datetime: {end_dt}", self.verbose)
        else:
            end_dt = end_date
        
        # Truncate any HH:MM:SS
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        _print_if_verbose(f"Truncated dates to midnight: {start_dt} to {end_dt}", self.verbose)
        
        # Calculate total units in the date range
        if granularity is not None:
            granularity = granularity[0]  # Get first letter
            _print_if_verbose(f"Using provided granularity: {granularity}", self.verbose)
            
            # Get max_units for the provided granularity
            if granularity not in self.rules:
                raise ValueError(f"Invalid granularity: {granularity}. Must be one of: {list(self.rules.keys())}")
                
            max_units = self.rules[granularity]['max_records']
            _print_if_verbose(f"Maximum units for {granularity}: {max_units}", self.verbose)
            
            # Calculate total units based on the granularity
            total_units_result = self.calculate_total_units(start_dt, end_dt, granularity)
            total_units = total_units_result['num_periods']
            _print_if_verbose(f"Total units needed: {total_units}", self.verbose)
                
            # Calculate number of blocks needed, rounding up
            blocks = math.ceil(total_units / max_units)
            _print_if_verbose(f"Number of blocks needed: {blocks}", self.verbose)
        else:
            # Calculate the time range in days
            days_diff = (end_dt - start_dt).days
            _print_if_verbose(f"Days between dates: {days_diff}", self.verbose)
            
            # Determine granularity based on rules in order
            for code, rule in self.rules.items():
                if 'max_days' in rule and rule['max_days'] is not None:
                    if rule['max_inclusive']:
                        if days_diff <= rule['max_days']:
                            granularity = code
                            max_units = rule['max_records']
                            _print_if_verbose(f"Selected granularity {code} (inclusive rule, days_diff={days_diff} <= max_days={rule['max_days']})", self.verbose)
                            break
                    else:
                        if days_diff < rule['max_days']:
                            granularity = code
                            max_units = rule['max_records']
                            _print_if_verbose(f"Selected granularity {code} (exclusive rule, days_diff={days_diff} < max_days={rule['max_days']})", self.verbose)
                            break
                else:
                    # Last rule (monthly) has no max_days
                    granularity = code
                    max_units = float('inf')  # No limit for monthly
                    _print_if_verbose(f"Selected granularity {code} (fallback rule with no max_days)", self.verbose)
                    break
            blocks = 1  # Single block when granularity is calculated automatically
        
        # Create appropriate DateTimeIndex and PeriodIndex based on granularity
        datetime_index, period_index = self.create_time_indices(start_dt, end_dt, granularity)
        
        return {
            "granularity": granularity,
            "datetime_index": datetime_index,
            "period_index": period_index,
            "max_units": max_units,
            "blocks": blocks
        }
    
    def get_max_period_by_granularity(
        self,
        granularity: str,
        periods: int,
        start_dt: datetime
    ) -> Dict[str, Union[datetime, pd.PeriodIndex]]:
        """
        Get the maximum period for a given granularity, number of periods, and start date.
        
        Args:
            granularity (str): Time granularity code ('h', 'D', 'W', 'M')
            periods (int): Number of periods to calculate
            start_dt (datetime): Start date
            
        Returns:
            Dict[str, Union[datetime, pd.PeriodIndex]]: Dictionary containing:
                - start_dt: Start datetime
                - end_dt: End datetime
                - period_index: The period index spanning the range
        """
        _print_if_verbose(f"Calculating max period for granularity {granularity}, {periods} periods from {start_dt}", self.verbose)
        max_period_index = pd.period_range(start=start_dt, periods=periods, freq=granularity)
        end_dt = max_period_index.end_time[-1].round('s')
        _print_if_verbose(f"End datetime: {end_dt}", self.verbose)
        _print_if_verbose(f"Period index length: {len(max_period_index)}", self.verbose)
        
        return {
            "start_dt": start_dt,
            "end_dt": end_dt,
            "period_index": max_period_index
        }