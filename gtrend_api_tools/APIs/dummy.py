from datetime import datetime, timedelta
from typing import Union, List, Optional, Dict, Any
import pandas as pd
from ..utils import calculate_search_granularity
from .base_classes import API_Call
from .api_utils import standard_dict_to_df, sinc_data
import numpy as np

class DummyApi(API_Call):
    """
    A dummy API class that returns fake data for testing purposes.
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
        print_func: Optional[callable] = None,
        tor_control_password: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            api_key=api_key,
            proxy=proxy,
            change_identity=change_identity,
            request_delay=request_delay,
            geo=geo,
            cat=cat,
            gprop=gprop,
            language=language,
            tz=tz,
            no_cache=no_cache,
            region=region,
            verbose=verbose,
            print_func=print_func,
            tor_control_password=tor_control_password,
            api_endpoint=api_endpoint,
            **kwargs
        )

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        fill_value: Union[int, str] = 'sinc'
    ) -> 'DummyApi':
        """
        Generate dummy data for testing purposes.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up. Can be a single term, a comma-separated string of terms, or a list of terms. We only use the number of terms to determine how many output dummy values to generate.
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            fill_value (Union[int, str]): If int, fill all values with this number.
                                         If "sinc", generate sinc wave data with
                                         num_zero_crossings based on number of search terms.
        
        Returns:
            DummyApi: Returns self for method chaining
        """
        # Convert search_term to list if it's a string
        if isinstance(search_term, str):
            search_term = [term.strip() for term in search_term.split(',')]
            
        # Convert dates to datetime if they're strings
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            
        # If no dates provided, use last 30 days
        if not start_date:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        # Calculate number of days
        days = (end_date - start_date).days + 1
        
        # Generate dates
        dates = [start_date + timedelta(days=i) for i in range(days)]
        
        # Generate data in the format expected by standard_dict_to_df
        self.data = []
        
        if fill_value == "sinc":
            # Generate N sinc waves (one for each term)
            term_values = []
            for i, term in enumerate(search_term):
                # Each term gets a different number of zero crossings
                num_zero_crossings = i + 2  # First term gets 2, second gets 3, etc.
                values = sinc_data(num_zero_crossings, 100, 0, days)
                # Round to 2 decimal places
                values = np.round(values, 2)
                term_values.append(values)
            
            # Transpose the values so we have D groups of N terms
            term_values = np.array(term_values).T
            
            # Create entries for each date
            for i, date in enumerate(dates):
                entry = {
                    'date': date.strftime('%Y-%m-%d'),
                    'values': [
                        {
                            'query': term,
                            'value': float(term_values[i][j])  # Convert numpy float to Python float
                        }
                        for j, term in enumerate(search_term)
                    ]
                }
                self.data.append(entry)
        else:
            # Fill with constant value
            for date in dates:
                entry = {
                    'date': date.strftime('%Y-%m-%d'),
                    'values': [
                        {
                            'query': term,
                            'value': fill_value
                        }
                        for term in search_term
                    ]
                }
                self.data.append(entry)
            
        # Store the same data as raw_data for consistency
        self.raw_data = self.data
        
        # Store search history
        self.search_history.append({
            'terms': search_term,
            'start_date': start_date,
            'end_date': end_date,
            'fill_value': fill_value
        })
        
        return self 