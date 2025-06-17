import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any, List, Tuple
from dateutil.parser import parse, ParserError

def _print_if_verbose(message: str, verbose: bool = False) -> None:
    """
    Print message if verbose is True.
    
    Args:
        message (str): Message to print
        verbose (bool): Whether to print the message
    """
    if verbose:
        print(message)

class DateRange:
    """
    A class to handle date range operations and standardization.
    """
    def __init__(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        granularity: str = 'D',
        range_space: str = ' ',
        verbose: bool = False
    ):
        self.original_date_str: Optional[str] = None
        self.original_date_cleaned: Optional[str] = None
        self.start_date: Optional[str] = None
        self.end_date: Optional[str] = None
        self.start_date_dt: Optional[datetime] = None
        self.end_date_dt: Optional[datetime] = None
        self.start_incomplete: bool = True
        self.end_incomplete: bool = True
        self.formatted_range_ymd: Optional[str] = None
        self.formatted_range_mdy: Optional[str] = None
        self.granularity: str = granularity[0]  # Default to daily granularity
        self.range_space: str = range_space

        # Initialize dates if provided
        # Note that if neither start_date nor end_date is provided, we leave those attributes as None.
        if start_date is not None or end_date is not None:
            if isinstance(start_date, datetime) and isinstance(end_date, datetime):
                self._init_from_dt([start_date, end_date])
            elif isinstance(start_date, datetime):
                self._init_from_dt(start_date)
            elif isinstance(end_date, datetime):
                raise ValueError("Cannot initialize with only an end date")
            else:
                # Handle string dates
                date_str = f"{start_date or ''} {end_date or ''}".strip()
                if date_str:
                    self._init_from_str(date_str, verbose)

    @classmethod
    def from_str(cls, date_str: str, granularity: str = 'D', range_space: str = ' ', verbose: bool = False) -> 'DateRange':
        """
        Create a DateRange instance from a date string.
        
        Args:
            date_str (str): Date range string in format like "Dec 31, 2023 - Jan 6, 2024" or "Jan 7 - 13, 2024"
            range_space (str): The string to use between dates in the range. Defaults to a single space.
            granularity (str): The granularity of the date range. One of: 's' (seconds), 'm' (minutes), 'h' (hourly), 
                             'D' (daily), 'W' (weekly), 'M' (monthly), 'Q' (quarterly), 'Y' (yearly), 'X' (decade).
                             Defaults to 'D'.
            verbose (bool): Whether to print verbose debug information. Defaults to False.
            
        Returns:
            DateRange: A new DateRange instance
            
        Raises:
            ValueError: If the date string cannot be parsed
        """
        dr = cls(granularity=granularity, range_space=range_space, verbose=verbose)
        dr._init_from_str(date_str, verbose)
        return dr

    @classmethod
    def from_dt(cls, dt: Union[datetime, List[datetime], Tuple[datetime, datetime]], granularity: str = 'D', range_space: str = ' ', verbose: bool = False) -> 'DateRange':
        """
        Create a new DateRange instance from a datetime object or a pair of datetime objects.
        
        Args:
            dt (Union[datetime, List[datetime], Tuple[datetime, datetime]]): Either a single datetime object
                or a list/tuple of two datetime objects
            range_space (str): The string to use between dates in the range. Defaults to a single space.
            granularity (str): The granularity of the date range. One of: 's' (seconds), 'm' (minutes), 'h' (hourly), 
                             'D' (daily), 'W' (weekly), 'M' (monthly), 'Q' (quarterly), 'Y' (yearly), 'X' (decade).
                             Defaults to 'D'.
            verbose (bool): Whether to print verbose debug information. Defaults to False.
            
        Returns:
            DateRange: A new DateRange instance
            
        Raises:
            ValueError: If the input is not a datetime or a list/tuple of exactly two datetimes
        """
        dr = cls(granularity=granularity, range_space=range_space, verbose=verbose)
        dr._init_from_dt(dt)
        return dr

    def _init_from_dt(self, dt: Union[datetime, List[datetime], Tuple[datetime, datetime]]) -> None:
        """
        Initialize this DateRange instance from a datetime object or a pair of datetime objects.
        This is a private method used by both __init__ and from_dt.
        
        Args:
            dt (Union[datetime, List[datetime], Tuple[datetime, datetime]]): Either a single datetime object
                or a list/tuple of two datetime objects
            
        Raises:
            ValueError: If the input is not a datetime or a list/tuple of exactly two datetimes
        """
        # Handle single datetime
        if isinstance(dt, datetime):
            self.original_date_str = dt.isoformat()
            self.original_date_cleaned = make_clean_date_str(self.original_date_str)
            dt = self._zero_time_if_needed(dt)
            self.start_date_dt = dt
            self.start_incomplete = False
            self.end_incomplete = True
            self.make_time_range(dt)
            return
            
        # Handle list/tuple of datetimes
        if isinstance(dt, (list, tuple)) and len(dt) == 2 and all(isinstance(d, datetime) for d in dt):
            start_date_dt, end_date_dt = dt
            self.original_date_str = f"{start_date_dt.isoformat()}{self.range_space}{end_date_dt.isoformat()}"
            self.original_date_cleaned = f"{make_clean_date_str(start_date_dt.isoformat())}{self.range_space}{make_clean_date_str(end_date_dt.isoformat())}"
            start_date_dt = self._zero_time_if_needed(start_date_dt)
            end_date_dt = self._zero_time_if_needed(end_date_dt)
            self.start_date_dt = start_date_dt
            self.end_date_dt = end_date_dt
            self.start_incomplete = False
            self.end_incomplete = False
            self.make_time_range(start_date_dt, end_date_dt)
            return
            
        raise ValueError("Input must be either a datetime object or a list/tuple of exactly two datetime objects")

    def _zero_time_if_needed(self, dt_obj: datetime) -> datetime:
        """
        Helper method to zero out time components if needed based on granularity.
        
        Args:
            dt_obj (datetime): The datetime object to potentially zero out
            
        Returns:
            datetime: The datetime object with time components zeroed out if needed
        """
        if self.granularity not in ['h', 'm', 's']:
            return dt_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt_obj

    def make_time_range(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None, 
    ) -> 'DateRange':
        """
        Convert start_date and end_date into formatted time range strings and set instance attributes.
        If dates are strings, they will be parsed into datetime objects.
        Every instance of DateRange should use this method to properly set its date or time range attributes.
        
        Args:
            start_date (Optional[Union[str, datetime]]): Start date. If string, will be parsed with dateutil.parser
            end_date (Optional[Union[str, datetime]]): End date. If string, will be parsed with dateutil.parser
            
        Returns:
            DateRange: Returns self for method chaining
            
        Raises:
            ValueError: If neither start_date nor end_date is provided
            ValueError: If self.granularity is not one of: 's' (seconds), 'm' (minutes), 'h' (hourly), 
                       'D' (daily), 'W' (weekly), 'M' (monthly), 'Q' (quarterly), 'Y' (yearly), 'X' (decade)
        """
        # Check if any dates are provided
        if not start_date and not end_date:
            raise ValueError("At least one date must be provided")

        # default datetime object for parser is january 1 of current year and has hour zero
        current_year = datetime.now().year
        default_datetime = datetime(current_year, 1, 1, 0, 0, 0)

        # Parse string dates into datetime objects
        if isinstance(start_date, str):
            start_date = parse(start_date, default=default_datetime)
        if isinstance(end_date, str):
            end_date = parse(end_date, default=default_datetime)
        
        # Truncate by provided granularity.
        if self.granularity == 's':
            # For seconds granularity:
            # - Both start and end dates are rounded down to the nearest second
            if start_date:
                start_date = start_date.replace(microsecond=0)
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%dT%H:%M:%S")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%YT%H:%M:%S")
                self.start_date_dt = start_date
            if end_date:
                end_date = end_date.replace(microsecond=0)
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%dT%H:%M:%S")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%YT%H:%M:%S")
                self.end_date_dt = end_date
        elif self.granularity == 'm':
            # For minutes granularity:
            # - Both start and end dates are rounded down to the nearest minute
            if start_date:
                start_date = start_date.replace(second=0, microsecond=0)
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%dT%H:%M")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%YT%H:%M")
                self.start_date_dt = start_date
            if end_date:
                end_date = end_date.replace(second=0, microsecond=0)
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%dT%H:%M")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%YT%H:%M")
                self.end_date_dt = end_date
        elif self.granularity == 'h':
            # For hourly granularity:
            # - Both start and end dates are rounded down to the nearest hour
            if start_date:
                start_date = start_date.replace(minute=0, second=0, microsecond=0)
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%dT%H")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%YT%H")
                self.start_date_dt = start_date
            if end_date:
                end_date = end_date.replace(minute=0, second=0, microsecond=0)
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%dT%H")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%YT%H")
                self.end_date_dt = end_date
        elif self.granularity == 'D':
            # For daily granularity:
            # - Both start and end dates are rounded down to the start of the day
            if start_date:
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%d")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%Y")
                self.start_date_dt = start_date
            if end_date:
                end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%d")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%Y")
                self.end_date_dt = end_date
        elif self.granularity == 'W':
            # For weekly granularity:
            # - Start date is truncated to previous Sunday (week start)
            # - End date is rounded up to next Saturday (week end)
            if start_date:
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                # Calculate days to subtract to get to previous Sunday (weekday 6)
                days_to_subtract = (start_date.weekday() + 1) % 7
                start_date = (start_date - timedelta(days=days_to_subtract)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%d")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%Y")
                self.start_date_dt = start_date
            if end_date:
                end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                # Calculate days to add to get to next Saturday (weekday 5)
                days_to_add = (5 - end_date.weekday()) % 7
                end_date = (end_date + timedelta(days=days_to_add)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%d")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%Y")
                self.end_date_dt = end_date
        elif self.granularity == 'M':
            # For monthly granularity:
            # - Start date is truncated to first day of the month
            # - End date is rounded to last day of the month
            if start_date:
                start_date = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%d")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%Y")
                self.start_date_dt = start_date
            if end_date:
                # Get the first day of next month
                if end_date.month == 12:
                    next_month = end_date.replace(year=end_date.year + 1, month=1, day=1)
                else:
                    next_month = end_date.replace(month=end_date.month + 1, day=1)
                # Subtract one day to get last day of current month
                end_date = (next_month - timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%d")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%Y")
                self.end_date_dt = end_date
        elif self.granularity == 'Q':
            # For quarterly granularity:
            # - Start date is truncated to first day of the quarter (Jan 1, Apr 1, Jul 1, Oct 1)
            # - End date is rounded to last day of the quarter (Mar 31, Jun 30, Sep 30, Dec 31)
            if start_date:
                # Calculate the first month of the quarter (0-based)
                quarter_start_month = ((start_date.month - 1) // 3) * 3 + 1
                start_date = start_date.replace(
                    month=quarter_start_month,
                    day=1,
                    hour=0, minute=0, second=0, microsecond=0
                )
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%d")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%Y")
                self.start_date_dt = start_date
            if end_date:
                # Calculate the last month of the quarter (0-based)
                quarter_end_month = ((end_date.month - 1) // 3 + 1) * 3
                # Get the first day of next quarter
                if quarter_end_month == 12:
                    next_quarter = end_date.replace(year=end_date.year + 1, month=1, day=1)
                else:
                    next_quarter = end_date.replace(month=quarter_end_month + 1, day=1)
                # Subtract one day to get last day of current quarter
                end_date = (next_quarter - timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%d")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%Y")
                self.end_date_dt = end_date
        elif self.granularity == 'Y':
            # For yearly granularity:
            # - Start date is truncated to January 1st
            # - End date is rounded to December 31st
            if start_date:
                start_date = start_date.replace(
                    month=1,
                    day=1,
                    hour=0, minute=0, second=0, microsecond=0
                )
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%d")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%Y")
                self.start_date_dt = start_date
            if end_date:
                end_date = end_date.replace(
                    month=12,
                    day=31,
                    hour=0, minute=0, second=0, microsecond=0
                )
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%d")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%Y")
                self.end_date_dt = end_date
        elif self.granularity == 'X':
            # For decade granularity:
            # - Start date is rounded down to the start of the decade (year ending in 0)
            # - End date is rounded to the end of the decade (last day of year ending in 9)
            if start_date:
                # Round down to start of decade
                decade_start = (start_date.year // 10) * 10
                start_date = start_date.replace(
                    year=decade_start,
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                self.formatted_start_date_ymd = start_date.strftime("%Y-%m-%d")
                self.formatted_start_date_mdy = start_date.strftime("%m/%d/%Y")
                self.start_date_dt = start_date
            if end_date:
                # Calculate first day of next decade
                next_decade = ((end_date.year // 10) + 1) * 10
                # Subtract one day to get last day of current decade
                end_date = (datetime(next_decade, 1, 1) - timedelta(days=1)).replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                self.formatted_end_date_ymd = end_date.strftime("%Y-%m-%d")
                self.formatted_end_date_mdy = end_date.strftime("%m/%d/%Y")
                self.end_date_dt = end_date
        else:
            raise ValueError(f"Invalid granularity: {self.granularity}")

        # Create formatted range strings
        if start_date and end_date:
            self.formatted_range_ymd = f"{self.formatted_start_date_ymd}{self.range_space}{self.formatted_end_date_ymd}"
            self.formatted_range_mdy = f"{self.formatted_start_date_mdy}{self.range_space}{self.formatted_end_date_mdy}"
        elif start_date:
            self.formatted_range_ymd = self.formatted_start_date_ymd
            self.formatted_range_mdy = self.formatted_start_date_mdy
        elif end_date:
            self.formatted_range_ymd = self.formatted_end_date_ymd
            self.formatted_range_mdy = self.formatted_end_date_mdy

        return self

    def _init_from_str(self, date_str: str, verbose: bool = False) -> None:
        """
        Initialize this DateRange instance from a date string.
        This is a private method used by both __init__ and from_str.
        
        Args:
            date_str (str): Date range string in format like "Dec 31, 2023 - Jan 6, 2024" or "Jan 7 - 13, 2024"
            verbose (bool): Whether to print verbose debug information
            
        Raises:
            ValueError: If the date string cannot be parsed
        """
        # First clean the unicode to ascii because serpapi returns some weird unicode characters
        clean_date_str = make_clean_date_str(date_str)
        self.original_date_str = date_str
        self.original_date_cleaned = clean_date_str

        # test for case like "2020-01-01 - 2020-01-07 or 2020-01-01 2020-01-07"
        if re.search(r'^\d{4}-\d{2}-\d{2}', clean_date_str):
            _print_if_verbose(f"Found ISO format date: {clean_date_str}", verbose)
            # extract the ISO format date
            self.start_date = re.search(r'^\d{4}-\d{2}-\d{2}', clean_date_str).group()
            self.start_date_dt = parse(self.start_date)
            # delete the first date from the string
            clean_date_str = clean_date_str.replace(self.start_date, '', 1).strip()
            # now see if there is another one
            if re.search(r'\d{4}-\d{2}-\d{2}', clean_date_str):
                self.end_date = re.search(r'\d{4}-\d{2}-\d{2}', clean_date_str).group()
                self.end_date_dt = parse(self.end_date)
                # delete the second date from the string
                clean_date_str = clean_date_str.replace(self.end_date, '', 1).strip()
        # test for case like "11/3/2021 - 11/10/2021"
        elif re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str):
            _print_if_verbose(f"Found MM/DD/YYYY format date: {clean_date_str}", verbose)
            self.start_date = re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str).group()
            self.start_date_dt = parse(self.start_date)
            # delete the first date from the string
            clean_date_str = clean_date_str.replace(self.start_date, '', 1).strip()
            # now see if there is another one
            if re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str):
                self.end_date = re.search(r'\d{1,2}/\d{1,2}/\d{4}', clean_date_str).group()
                self.end_date_dt = parse(self.end_date)
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
            self.start_date = parts[0] + front_digits + ', ' + back_year
            self.end_date = back_digits + parts[1]
        # test for case like "Jan 1 - 7, 2020"
        elif re.search(r'\d+\s*-\s*\d+', clean_date_str):
            _print_if_verbose(f"Found DD - DD format date: {clean_date_str}", verbose)
            parts = re.split(r'\d+\s*-\s*\d+', clean_date_str)
            splitter = re.search(r'\d+\s*-\s*\d+', clean_date_str).group()
            front_digits = re.search(r'\d+', splitter).group()
            back_digits = re.search(r'-\s*\d+', splitter).group().lstrip('-')
            back_year = re.search(r'\d+$', parts[1]).group()
            self.start_date = parts[0] + front_digits + ', ' + back_year
            self.end_date = back_digits + parts[1]
        # test for case like "Jan 1-Dec 7, 2020"
        elif re.search(r'\d+-[a-zA-Z]+', clean_date_str):
            _print_if_verbose(f"Found DD-MM format date: {clean_date_str}", verbose)
            parts = re.split(r'\d+-[a-zA-Z]+', clean_date_str)
            splitter = re.search(r'\d+-[a-zA-Z]+', clean_date_str).group()
            front_digits = re.search(r'\d+', splitter).group()
            back_letters = re.search(r'-[a-zA-Z]+', splitter).group().lstrip('-')
            back_year = re.search(r'\d+$', parts[1]).group()
            self.start_date = parts[0] + front_digits + ', ' + back_year
            self.end_date = back_letters + parts[1]
        # search for case like "Jan 1 - Dec 7, 2020"
        elif re.search(r'\d+\s*-\s*[a-zA-Z]+', clean_date_str):
            _print_if_verbose(f"Found DD - MM format date: {clean_date_str}", verbose)
            parts = re.split(r'\d+\s*-\s*[a-zA-Z]+', clean_date_str)
            splitter = re.search(r'\d+\s*-\s*[a-zA-Z]+', clean_date_str).group()
            front_digits = re.search(r'\d+', splitter).group()
            back_letters = re.search(r'-\s*[a-zA-Z]+', splitter).group().lstrip('-').strip()
            back_year = re.search(r'\d+$', parts[1]).group()
            self.start_date = parts[0] + front_digits + ', ' + back_year
            self.end_date = back_letters + parts[1]
        # if we get here we can assume there's only one date.
        else:
            _print_if_verbose(f"Found single date: {clean_date_str}", verbose)
            try:
                self.start_date = clean_date_str
                self.start_date_dt = parse(clean_date_str)
            except (ValueError, ParserError) as e:
                _print_if_verbose(f"Could not parse date string: {clean_date_str}", verbose)
                raise ValueError(f"Could not parse date string: {clean_date_str}") from e

        # Handle single date case
        if self.start_date and not self.end_date:
            self.start_incomplete = False
            self.end_incomplete = True
            self.formatted_range_ymd = self.start_date_dt.strftime("%Y-%m-%d")
            self.formatted_range_mdy = self.start_date_dt.strftime("%m/%d/%Y")
            return

        # Handle two dates case
        if self.start_date:
            try:
                self.start_date_dt = parse(self.start_date)
                self.start_incomplete = False
            except (ParserError):
                pass
        if self.end_date:
            try:
                self.end_date_dt = parse(self.end_date)
                self.end_incomplete = False
            except (ParserError):
                pass

        # Handle incomplete dates
        if self.start_incomplete and self.end_date:
            date_year = re.search(r'\d{4}\s*$', self.end_date).group()
            self.start_date = self.start_date + ', ' + date_year
            try:
                self.start_date_dt = parse(self.start_date)
                self.start_incomplete = False
            except (ParserError):
                pass

        if self.end_incomplete and self.start_date:
            date_month = re.search(r'[a-zA-Z]{2,}', self.start_date).group()
            self.end_date = date_month + ' ' + self.end_date
            try:
                self.end_date_dt = parse(self.end_date)
                self.end_incomplete = False
            except (ParserError):
                pass
        # Note: Once we get to this point, we have both string and datetime objects for start date,
        # and, if provided, also for end date.
        # Now that we have parsed that out of the string, we make all the different representations
        # of the date or time range.
        self.make_time_range(self.start_date_dt, self.end_date_dt)


def make_clean_date_str(date_str: str) -> str:
    """
    Clean a date string. The unicode characters are converted to ascii and the unicode dashes are replaced with ascii dashes.
    Cleanable unicode character values: \u2013\u2014\u2015\u2043\u2212\u23AF\u23E4\u2500\u2501\u2E3A\u2E3B\uFE58\uFE63\uFF0D\u007E
    Cleanable unicode characters: – — ― ⁄ − ⎯ ⎴ ⎵ ⸺ ⸻ ﹘ ﹣ － ~
    Args:
        date_str (str): Date string to clean
        
    Returns:
        str: Cleaned date string
    """
    fixable_dashes_escaped = '\u2013\u2014\u2015\u2043\u2212\u23AF\u23E4\u2500\u2501\u2E3A\u2E3B\uFE58\uFE63\uFF0D'
    fixable_dashes = '– — ― ⁄ − ⎯ ⎴ ⎵ ⸺ ⸻ ﹘ ﹣ －'
    fixable_nonprinting_escaped = '\u200B\u200C\u200D\u200E\u200F\u202A\u202B\u202C\u202D\u202E\u202F\u2060\u2061\u2062\u2063\u2064\u2065\u2066\u2067\u2068\u2069\u206A\u206B\u206C\u206D\u206E\u206F\u20F0\u20F1\u20F2\u20F3\u20F4\u20F5\u20F6\u20F7\u20F8\u20F9\u20FA\u20FB\u20FC\u20FD\u20FE\u20FF'

    date_str_unicode_normalized = unicodedata.normalize('NFKC', date_str).strip()
    if not date_str_unicode_normalized.isascii():
        for char in date_str_unicode_normalized:
            if char.isascii():
                pass
            elif char in fixable_dashes_escaped:
                print(f"Swapping '-' for non-ascii character: {char} ({char.encode('unicode_escape').decode('ascii')})")
            elif char in fixable_nonprinting_escaped:
                print(f"Swapping non-printing character: {char.encode('unicode_escape').decode('ascii')}")
    date_str_unicode_normalized = re.sub(f'[{fixable_dashes_escaped}]', '-', date_str_unicode_normalized)
    date_str_unicode_normalized = re.sub(f'[{fixable_nonprinting_escaped}]', ' ', date_str_unicode_normalized)
    date_str_unicode_normalized = re.sub(r'\s+', ' ', date_str_unicode_normalized)
    date_str_unicode_normalized = date_str_unicode_normalized.strip()
    return date_str_unicode_normalized