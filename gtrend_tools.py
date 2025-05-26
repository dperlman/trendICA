#! /opt/miniconda3/envs/trendspy/bin/python3

#import requests
import unicodedata
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
import time
from trendspy import Trends
import pandas as pd
import time
import socket
import os
import re
import math
import numpy as np


def search_google_trends(
    search_term: str,
    start_date: str,
    end_date: Optional[str] = None,
    duration_days: Optional[int] = 90,
    geo: Optional[str] = None,
    cat: Optional[str] = None,
    serpapi_api_key: Optional[str] = None,
    no_cache: bool = False,
    granularity: str = "day",
    n_iterations: int = 1,
    proxy: Optional[str] = None,
    change_identity: bool = True,
    request_delay: int = 4
) -> pd.DataFrame:
    """
    Search Google Trends for a given query, with optional multiple iterations.
    
    Args:
        search_term (str): The search term to look up in Google Trends
        start_date (str): Start date for the search (e.g. "2008-01-01")
        end_date (Optional[str]): End date for the search (e.g. "2025-04-21")
        duration_days (Optional[int]): Number of days to search from start_date if end_date not provided
        geo (Optional[str]): Geographic location for the search (e.g. "US")
        cat (Optional[str]): Category for the search
        serpapi_api_key (Optional[str]): Your SerpAPI API key. If provided, will use SerpAPI
        no_cache (bool): Whether to skip cached results (only used with SerpAPI)
        granularity (str): Time granularity for results, either "day" or "hour". Any other value will use the default API behavior.
        n_iterations (int): Number of times to perform the search. Defaults to 1
        proxy (Optional[str]): The proxy to use. If None, no proxy will be used
        change_identity (bool): Whether to change Tor identity between iterations. Only used if proxy is provided
        request_delay (int): Delay between requests in seconds
        
    Returns:
        pd.DataFrame: DataFrame containing the Google Trends data
    """
    # Determine time range
    if end_date is None:
        time_range = None  # Will be handled by search_google_trends_by_day_90
    else:
        time_range = f"{start_date} {end_date}"
    
    all_timeseries = []
    print(f"Collecting {n_iterations} timeseries for '{search_term}'...")
    
    for i in range(n_iterations):
        print(f"Iteration {i+1}/{n_iterations}")
        
        # Choose appropriate search function based on parameters
        if end_date is None:
            iteration_results = search_google_trends_by_day_90(
                search_term=search_term,
                start_date=start_date,
                duration_days=duration_days,
                geo=geo,
                cat=cat,
                serpapi_api_key=serpapi_api_key,
                no_cache=no_cache,
                proxy=proxy,
                change_identity=change_identity,
                request_delay=request_delay
            )
        elif granularity == "day":
            iteration_results = search_google_trends_by_day(
                search_term=search_term,
                time_range=time_range,
                geo=geo,
                cat=cat,
                serpapi_api_key=serpapi_api_key,
                no_cache=no_cache,
                proxy=proxy,
                change_identity=change_identity,
                request_delay=request_delay
            )
        elif granularity == "hour":
            iteration_results = search_google_trends_by_hour(
                search_term=search_term,
                time_range=time_range,
                geo=geo,
                cat=cat,
                serpapi_api_key=serpapi_api_key,
                no_cache=no_cache,
                proxy=proxy,
                change_identity=change_identity,
                request_delay=request_delay
            )
        else:
            iteration_results = search_google_trends_choose_api(
                search_term=search_term,
                time_range=time_range,
                geo=geo,
                cat=cat,
                serpapi_api_key=serpapi_api_key,
                no_cache=no_cache,
                request_delay=request_delay,
                proxy=proxy,
                change_identity=change_identity
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

    print(f"Combined df for '{search_term}' shape: {combined_df.shape}")
    return combined_df



def search_google_trends_choose_api(
    search_term: str,
    time_range: Optional[str] = None,
    geo: Optional[str] = None,
    cat: Optional[str] = None,
    serpapi_api_key: Optional[str] = None,
    no_cache: bool = False,
    request_delay: Optional[int] = None,
    proxy: Optional[str] = None,
    change_identity: Optional[bool] = None,
) -> Union[pd.DataFrame, Dict[str, Any]]:
    """
    Search Google Trends for a given query using either SerpAPI or trendspy.
    
    Args:
        search_term (str): The search term to look up in Google Trends
        time_range (Optional[str]): Time range for the search (e.g. "2008-01-01 2025-04-21")
        geo (Optional[str]): Geographic location for the search (e.g. "US")
        cat (Optional[str]): Category for the search
        serpapi_api_key (Optional[str]): Your SerpAPI API key. If provided, will use SerpAPI
        no_cache (bool): Whether to skip cached results (only used with SerpAPI)
        request_delay (Optional[int]): Delay between requests in seconds (only used with trendspy)
        proxy (Optional[str]): Proxy URL to use (only used with trendspy)
        change_identity (Optional[bool]): Whether to change Tor identity (only used with trendspy)
        
    Returns:
        Union[pd.DataFrame, Dict[str, Any]]: Either a DataFrame containing the Google Trends data,
        or a dictionary containing the raw API response
    """
    if serpapi_api_key:
        return search_google_trends_serpapi(
            serpapi_api_key=serpapi_api_key,
            search_term=search_term,
            time_range=time_range,
            geo=geo,
            cat=cat,
            no_cache=no_cache
        )
    else:
        return search_google_trends_trendspy(
            search_term=search_term,
            time_range=time_range,
            geo=geo,
            cat=cat,
            request_delay=request_delay,
            proxy=proxy,
            change_identity=change_identity
        )


def get_start_date_of_pair(date_str: str) -> str:
    """
    Extract the start date from a date range string.
    
    Args:
        date_str (str): Date range string in format like "Dec 31, 2023 – Jan 6, 2024" or "Jan 7 – 13, 2024"
        
    Returns:
        str: The start date as a string
    """
    
    # first clean the unicode to ascii because serpapi returns some weird unicode characters
    #print(f'Original Date String: {date_str.encode('ascii', 'xmlcharrefreplace').decode('utf-8')}')
    date_str = unicodedata.normalize('NFKC', date_str)
    # print(f'Cleaned Date String: {date_str}')
    
    # by default we will return the original date string
    original_date_str = date_str
    
    parts = date_str.split(" – ")
    # print(f'Date Parts: {parts}')
    
    # Handle case with full date range (e.g. "Dec 31, 2023 – Jan 6, 2024")
    if "," in parts[0]:
        # print(f'First one has comma: {parts[0]}')
        original_date_str =  parts[0]
    elif len(parts) == 2:
        start_date = parts[0]
        # Extract year from end date
        year = parts[1].split(", ")[1]
        # print(f'Partial date before range: {start_date}, {year}')
        original_date_str = f"{start_date}, {year}"
    # print(f'Cleaned date string before reformatting: {original_date_str}')
    # convert the date string to basically ISO format
    try:
        # print('Trying to convert to datetime object with format: "%b %d, %Y"')
        datetime_object = datetime.strptime(original_date_str, "%b %d, %Y")
    except ValueError:
        try:
            # print(f'Trying to convert to datetime object with format: "%m/%d/%Y"')
            datetime_object = datetime.strptime(original_date_str, "%m/%d/%Y")
        except ValueError:
            try:
                # print(f'Trying to convert to datetime object with format: "%b %Y"')
                datetime_object = datetime.strptime(original_date_str, "%b %Y")
            except ValueError:
                raise ValueError(f"Could not parse date string: {original_date_str}")
    
    output_date_str = datetime_object.strftime("%Y-%m-%d")

    # print(f"Original date string: {original_date_str} -> New date string: {output_date_str}")
    return output_date_str


def search_google_trends_serpapi(
    serpapi_api_key: str,
    search_term: str,
    time_range: Optional[str] = None,
    geo: Optional[str] = None,
    cat: Optional[str] = None,
    no_cache: bool = False,
) -> Union[pd.DataFrame, Dict[str, Any]]:
    """
    Search Google Trends for a given query using SerpAPI.
    
    Args:
        search_term (str): The search term to look up in Google Trends
        serpapi_api_key (str): Your SerpAPI API key
        no_cache (bool): Whether to skip cached results
        time_range (Optional[str]): Time range for the search (e.g. "2008-01-01 2025-04-21")
        geo (Optional[str]): Geographic location for the search (e.g. "US")
        
    Returns:
        Union[pd.DataFrame, Dict[str, Any]]: Either a DataFrame with the trends data or a dict containing an error message
    """
    from serpapi import GoogleSearch
    
    params = {
        "api_key": serpapi_api_key,
        "engine": "google_trends",
        "no_cache": str(no_cache).lower(),
        "q": search_term,
        "hl": "en",
        "geo": geo or "US",
        "cat": cat,
        "date": time_range
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    print(results)
    
    # Check if there's an error in the results
    if isinstance(results, dict) and "error" in results:
        return results
        
    interest_over_time = results['interest_over_time']['timeline_data']
    # print(interest_over_time[0]['date'])
    # print(interest_over_time[0]['timestamp'])
    # print(datetime.fromtimestamp(int(interest_over_time[0]['timestamp'])))
    
    # Extract values and create DataFrame with date as index
    dates = []
    values = []
    for item in interest_over_time:
        date_str = get_start_date_of_pair(item['date'])

        dates.append(date_str)
        
        values.append({
            search_term.replace(" ", "_"): item['values'][0]['extracted_value'] if item['values'] else 0
        })
    
    # print(dates)
    df = pd.DataFrame(values, index=pd.to_datetime(dates))
    
    return df


def search_google_trends_trendspy(
    search_term: Union[str, List[str]], 
    time_range: Optional[str] = None,
    geo: Optional[str] = None,
    cat: Optional[str] = None,
    request_delay: int = 4,
    proxy: str = "localhost:9050",
    change_identity: bool = False
) -> Union[pd.DataFrame, Dict[str, Any]]:
    """
    Search Google Trends for a given query using a specified proxy.
    
    Args:
        search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends.
            Can be a single string or a list of strings for comparing multiple terms.
        proxy (str, optional): The proxy to use in the format "host:port". Defaults to "localhost:9050".
        time_range (str, optional): The time range for the search. Can be one of:
            - "now 1-H" (last hour)
            - "now 1-d" (last day)
            - "now 7-d" (last week)
            - "today 1-m" (last month)
            - "today 3-m" (last 3 months)
            - "today 12-m" (last 12 months)
            - "today 5-y" (last 5 years)
            - "all" (since 2004)
            Defaults to None (uses trendspy's default).
        geo (str, optional): Geographic location code (e.g., 'US', 'GB', 'US-NY').
            Defaults to None (worldwide).
        cat (str, optional): Category ID for filtering results.
            Defaults to None (all categories).
        request_delay (int, optional): Delay between requests in seconds. Defaults to 4.
        change_identity (bool, optional): Whether to change Tor identity before making the request.
            Defaults to False.
    
    Returns:
        Union[pd.DataFrame, Dict[str, Any]]: Either a DataFrame with the trends data or a dict containing an error message
    """
    # First try block for changing Tor identity
    if change_identity and proxy:
        try:
            change_tor_identity()
            # Add a delay after changing identity to ensure it takes effect
            time.sleep(5)
        except Exception as e:
            error_msg = f"Error changing Tor identity: {str(e)}"
            print(error_msg)
            return {"error": error_msg}
    
    # Second try block for the actual search
    try:
        # Configure the proxy for the request
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        
        trends = Trends(proxies=proxies, request_delay=request_delay)
        
        # Prepare the parameters for interest_over_time
        params = {}
        if time_range:
            params['timeframe'] = time_range
        if geo:
            params['geo'] = geo
        if cat:
            params['cat'] = cat
        
        # Perform the search with the appropriate parameters
        results = trends.interest_over_time(search_term, **params)
        
        # Replace spaces with underscores in column names if results is a DataFrame
        if isinstance(results, pd.DataFrame):
            results.columns = [col.replace(" ", "_") for col in results.columns]
        
        return results
    
    except Exception as e:
        error_msg = str(e)[:100]
        print(error_msg)
        return {"error": error_msg}


def search_google_trends_by_day(
    search_term: str,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    geo: Optional[str] = None,
    cat: Optional[str] = None,
    serpapi_api_key: Optional[str] = None,
    no_cache: bool = False,
    request_delay: Optional[int] = None,
    proxy: Optional[str] = None,
    change_identity: Optional[bool] = None,
    stagger: int = 0,
    trim: bool = True,
    scale: bool = True,
    combine: bool = True,
    final_scale: bool = True,
    round: int = 2,
    method: str = "MAD",
    raw_groups: bool = False,
    dry_run: bool = False,
) -> Union[pd.DataFrame, List[List[pd.DataFrame]], Dict[str, str], List[datetime]]:
    """
    Perform a Google Trends search with daily granularity over multiple 90-day intervals.
    
    Args:
        search_term (str): The search term to look up in Google Trends
        start_date (Union[str, datetime]): The start date in YYYY-MM-DD format or datetime object
        end_date (Union[str, datetime]): The end date in YYYY-MM-DD format or datetime object
        geo (Optional[str]): Geographic location for the search (e.g. "US")
        cat (Optional[str]): Category for the search
        serpapi_api_key (Optional[str]): Your SerpAPI API key
        no_cache (bool): Whether to skip cached results
        request_delay (Optional[int]): Delay between requests in seconds
        proxy (Optional[str]): Proxy URL to use
        change_identity (Optional[bool]): Whether to change Tor identity
        stagger (int): Number of overlapping intervals. 0 means no overlap, 1 means 50% overlap,
                      2 means 67% overlap, etc.
        trim (bool): Whether to drop rows with NA values because of the staggering. Defaults to True.
        scale (bool): Whether to scale overlapping intervals. Defaults to True.
        combine (bool): Whether to average all columns into a single column. Defaults to True.
        final_scale (bool): Whether to scale the final result so maximum value is 100. Defaults to True.
        round (int): Number of decimal places to round values to. Defaults to 2.
        method (str): Method to use for scaling overlapping intervals. Options are 'SSD' or 'MAD'. Defaults to 'MAD'.
        raw_groups (bool): If True, returns the raw stagger groups without concatenating. Defaults to False.
        dry_run (bool): If True, returns a list of start dates that would be searched instead of making API calls.
        
    Returns:
        Union[pd.DataFrame, List[List[pd.DataFrame]], Dict[str, str], List[datetime]]: Either a combined dataframe containing all timeseries data,
        the raw stagger groups if raw_groups is True, an error dictionary if an error occurs, or a list of start dates if dry_run is True
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
    
    # Calculate number of 90-day intervals needed
    total_days = (end_dt - start_dt).days
    base_intervals = math.ceil(total_days / 90)
    if stagger > 0:
        base_intervals = base_intervals + 1
    
    # Calculate overlap factor and number of intervals
    if stagger == 0:
        overlap_factor = 0
        intervals = base_intervals
    else:
        overlap_factor = 1 / (stagger + 1)
        intervals = base_intervals + stagger
    
    # Calculate the earliest start date needed to ensure full coverage
    earliest_start = start_dt - timedelta(days=math.floor(90 * overlap_factor * stagger)) if stagger > 0 else start_dt
    
    # Create list to store start dates
    start_dates = []
    
    # First collect the base intervals
    current_start = earliest_start
    for i in range(base_intervals):
        start_dates.append(current_start)
        current_start = current_start + timedelta(days=90)
    
    # If stagger > 0, collect additional overlapping intervals
    if stagger > 0:
        for s in range(1, stagger + 1):
            # Calculate offset for this stagger group using overlap_factor
            offset_days = math.floor(90 * overlap_factor * s)
            current_start = earliest_start + timedelta(days=offset_days)
            
            # Collect intervals for this stagger group
            for i in range(base_intervals):
                start_dates.append(current_start)
                current_start = current_start + timedelta(days=90)
    
    if dry_run:
        print(f"Would perform {len(start_dates)} searches with the following start dates:")
        for i, date in enumerate(start_dates, 1):
            print(f"{i}. {date.strftime('%Y-%m-%d')}")
    
    # Create list to store results for each stagger group
    stagger_groups = [[] for _ in range(stagger + 1)]
    
    # Initialize search counter
    search_count = 0
    
    # First collect the base intervals
    current_start = earliest_start
    for i in range(base_intervals):
        search_count += 1
        if dry_run:
            # Create a 90-day range for this interval
            interval_end = current_start + timedelta(days=89)
            interval_range = pd.date_range(start=current_start, end=interval_end, freq='D')
            result = pd.DataFrame(0, index=interval_range, columns=[search_term.replace(" ", "_")])
        else:
            result = search_google_trends_by_day_90(
                search_term=search_term,
                start_date=current_start,
                geo=geo,
                cat=cat,
                serpapi_api_key=serpapi_api_key,
                no_cache=no_cache,
                request_delay=request_delay,
                proxy=proxy,
                change_identity=change_identity
            )
        
        # Check for error in result
        if isinstance(result, dict):
            result['search_count'] = search_count
            print(f"Error in search: {result}")
            return result
        
        # Add to first stagger group
        stagger_groups[0].append(result)
        current_start = current_start + timedelta(days=90)
    
    # If stagger > 0, collect additional overlapping intervals
    if stagger > 0:
        for s in range(1, stagger + 1):
            # Calculate offset for this stagger group using overlap_factor
            offset_days = math.floor(90 * overlap_factor * s)
            current_start = earliest_start + timedelta(days=offset_days)
            
            # Collect intervals for this stagger group
            for i in range(base_intervals):
                search_count += 1
                if dry_run:
                    # Create a 90-day range for this interval
                    interval_end = current_start + timedelta(days=89)
                    interval_range = pd.date_range(start=current_start, end=interval_end, freq='D')
                    result = pd.DataFrame(0, index=interval_range, columns=[search_term.replace(" ", "_")])
                else:
                    result = search_google_trends_by_day_90(
                        search_term=search_term,
                        start_date=current_start,
                        geo=geo,
                        cat=cat,
                        serpapi_api_key=serpapi_api_key,
                        no_cache=no_cache,
                        request_delay=request_delay,
                        proxy=proxy,
                        change_identity=change_identity
                    )
                
                # Check for error in result
                if isinstance(result, dict):
                    result['search_count'] = search_count
                    print(f"Error in search: {result}")
                    return result
                
                stagger_groups[s].append(result)
                current_start = current_start + timedelta(days=90)
    
    if stagger > 0 and scale and not dry_run:
        stagger_groups = scale_stagger_groups(stagger_groups, method)

    if raw_groups:
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
            
        if combine:
            # Average all columns into a single column
            result_df = pd.DataFrame(result_df.mean(axis=1), columns=[search_term.replace(" ", "_")])
            
        if final_scale:
            # Scale the result so maximum value is 100
            max_val = result_df.max().max()
            if max_val > 0:  # Avoid division by zero
                result_df = result_df * (100 / max_val)
            
        # Round all values to specified number of decimal places
        if round is not None:
            result_df = result_df.round(round)
        return result_df
    return pd.DataFrame()


def scale_stagger_groups(stagger_groups: List[List[pd.DataFrame]], method: str = "MAD", reference: Union[str, int] = "first") -> List[List[pd.DataFrame]]:
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
        working_groups[i] = scale_series(ref_df, current_df, method=method)
    
    # Scale backward from reference
    for i in range(ref_idx - 1, -1, -1):
        ref_df = working_groups[i + 1]
        current_df = working_groups[i]
        working_groups[i] = scale_series(ref_df, current_df, method=method)
    
    # Reshape back into original structure
    result_groups = [[] for _ in range(len(stagger_groups))]
    for flat_idx, (group_idx, interval_idx) in enumerate(scaling_order):
        # Ensure the group has enough space
        while len(result_groups[group_idx]) <= interval_idx:
            result_groups[group_idx].append(None)
        result_groups[group_idx][interval_idx] = working_groups[flat_idx]
    
    return result_groups


def search_google_trends_by_day_90(
    search_term: str,
    start_date: Union[str, datetime],
    duration_days: int = 90,
    geo: Optional[str] = None,
    cat: Optional[str] = None,
    serpapi_api_key: Optional[str] = None,
    no_cache: bool = False,
    request_delay: Optional[int] = None,
    proxy: Optional[str] = None,
    change_identity: Optional[bool] = None,
) -> pd.DataFrame:
    """
    Perform a Google Trends search with daily granularity over a 90-day period.
    
    Args:
        search_term (str): The search term to look up in Google Trends.
        start_date (str): The start date in YYYY-MM-DD format.
        duration_days (int, optional): Number of days to search. Defaults to 90.
        proxy (str, optional): The proxy to use. If None, no proxy will be used. Defaults to None.
        geo (str, optional): The geographic location to search in. Defaults to None.
        cat (str, optional): The category to search in. Defaults to None.
        request_delay (int, optional): Delay in seconds between requests. Defaults to None.
        change_identity (bool, optional): Whether to change Tor identity before making the request.
            Defaults to False.
    
    Returns:
        pd.DataFrame: A dataframe containing the timeseries data with daily granularity.
    """
    # Convert start_date to datetime if it's a string, otherwise use as is
    if isinstance(start_date, str):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = start_date
    
    # Calculate end_date (90 days total, that's why we add 89 days, because it includes start and end)
    end_dt = start_dt + timedelta(days=89)
    end_date = end_dt.strftime("%Y-%m-%d")
    
    # Create the time range string
    time_range = f"{start_dt.strftime('%Y-%m-%d')} {end_date}"
    # Perform the search
    results = search_google_trends_choose_api(
        search_term=search_term,
        time_range=time_range,
        proxy=proxy,
        geo=geo,
        cat=cat,
        request_delay=request_delay,
        change_identity=change_identity,
        no_cache=no_cache,
        serpapi_api_key=serpapi_api_key
    )
    
    return results


def scale_series(series1: pd.Series, series2: pd.Series, method: str = "MAD") -> pd.Series:
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
        print(f"Original sum of squared differences: {original_diff}")
        
        # Calculate scale factor that minimizes sum of squared differences
        # Using the formula: scale = sum(x*y) / sum(y*y)
        scale_factor = np.sum(x * y) / np.sum(y * y)
        
        # Apply scale factor to second series
        scaled_series2 = series2 * scale_factor
        
        # Calculate final sum of squared differences
        final_diff = np.sum((x - scaled_series2.loc[common_dates].values) ** 2)
        print(f"Final sum of squared differences: {final_diff}")
    else:  # MAD
        # Calculate original median absolute difference
        original_diff = np.median(np.abs(x - y))
        print(f"Original median absolute difference: {original_diff}")
        
        # Use iterative optimization to find scale factor that minimizes MAD
        from scipy.optimize import minimize_scalar
        
        def mad_objective(scale):
            return np.median(np.abs(x - y * scale))
        
        result = minimize_scalar(mad_objective)
        scale_factor = result.x
        
        # Apply scale factor to second series
        scaled_series2 = series2 * scale_factor
        
        # Calculate final median absolute difference
        final_diff = np.median(np.abs(x - scaled_series2.loc[common_dates].values))
        print(f"Final median absolute difference: {final_diff}")
    
    return scaled_series2



def search_google_trends_by_hour(
    search_term: str,
    start_date: Union[str, datetime],
    geo: Optional[str] = None,
    cat: Optional[str] = None,
    serpapi_api_key: Optional[str] = None,
    no_cache: bool = False,
    request_delay: Optional[int] = None,
    proxy: Optional[str] = None,
    change_identity: Optional[bool] = None,
) -> pd.DataFrame:
    """
    Perform a Google Trends search with hourly granularity over a 7-day period.
    
    Args:
        search_term (str): The search term to look up in Google Trends.
        start_date (str): The start date in YYYY-MM-DD format.
        proxy (str, optional): The proxy to use. If None, no proxy will be used. Defaults to None.
        geo (str, optional): The geographic location to search in. Defaults to None.
        cat (str, optional): The category to search in. Defaults to None.
        request_delay (int, optional): Delay in seconds between requests. Defaults to None.
        change_identity (bool, optional): Whether to change Tor identity before making the request.
            Defaults to False.
    
    Returns:
        pd.DataFrame: A dataframe containing the timeseries data with hourly granularity.
    """
    # Convert start_date to datetime if it's a string, otherwise use as is
    if isinstance(start_date, str):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = start_date
    
    # Calculate end_date (7 days later, non-inclusive)
    end_dt = start_dt + timedelta(days=7) - timedelta(hours=1)

    # Convert to ISO format strings
    start_date = start_dt.strftime("%Y-%m-%dT%H")
    end_date = end_dt.strftime("%Y-%m-%dT%H")
    
    # Create the time range string
    time_range = f"{start_date} {end_date}"
    print(time_range)

    # Perform the search
    results = search_google_trends_choose_api(
        search_term=search_term,
        time_range=time_range,
        proxy=proxy,
        geo=geo,
        cat=cat,
        request_delay=request_delay,
        change_identity=change_identity,
        no_cache=no_cache,
        serpapi_api_key=serpapi_api_key
    )
    
    return results


def save_to_csv(combined_df: pd.DataFrame, search_term: str, path: Optional[str] = None, comment: Optional[str] = None) -> None:
    # Save the dataframe to a CSV file if requested
    # Create a filename with the search term and current ISO date
    current_date = datetime.now().strftime("%Y-%m-%d")
    formatted_utc_gmtime = time.strftime("%Y-%m-%dT%H-%MUTC", time.gmtime())

    # Replace spaces with underscores in the search term for the filename
    safe_search_term = search_term.replace(" ", "_")
    #filename = f"{safe_search_term}_on_{current_date}.csv"
    filename = f"{safe_search_term}_at_{formatted_utc_gmtime}.csv"
    filename = numbered_file_name(filename, path=path)
    
    # Join path if provided, otherwise use filename directly
    full_path = os.path.join(path, filename) if path else filename
    
    # First write the comment if provided
    if comment:
        with open(full_path, 'w') as f:
            f.write(f"# {comment}\n")
    
    # Save the dataframe to the CSV file
    combined_df.to_csv(full_path, index=True, mode='a')
    print(f"\nData saved to {full_path}")
    return filename


def numbered_file_name(orig_name: str, n_digits: int = 3, path: Optional[str] = None) -> str:
    """
    Generate a numbered filename by finding the next available number in the directory.
    If filename ends with _i### pattern, use the next available number. If no number pattern exists,
    add _i### pattern with specified digits. Number of digits is enforced in both cases.
    
    Args:
        orig_name (str): The original filename.
        n_digits (int): Number of digits to use for the counter. Defaults to 3.
        path (str, optional): Directory path to search for existing files. Defaults to None (current directory).
        
    Returns:
        str: New filename with the next available number.
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
    

def change_tor_identity():
    """
    Change the Tor identity by connecting to the Tor control port and sending a NEWNYM signal.
    Includes error handling and retry logic.
    """
    from stem.control import Controller
    from stem import Signal
    
    password="controlpass" # This is the password for the Tor control port

    try:
        # Try to connect to the Tor control port
        with Controller.from_port(port=9051) as controller:
            # Authenticate with the controller
            # If you have a password set in your torrc file, uncomment and use the line below
            controller.authenticate(password=password)
            
            # If no password is set, use this line instead
            # controller.authenticate()
            
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


def add_months(date_input: Union[str, datetime], months: int) -> str:
    """
    Add a specified number of months to a date, then subtract 1 day.
    If input day is 1, this effectively gives last day of previous month.
    
    Args:
        date_input (Union[str, datetime]): Input date as ISO format string or datetime object
        months (int): Number of months to add
        
    Returns:
        str: New date as ISO format string (YYYY-MM-DD)
    """
    # Convert string to datetime if needed
    if isinstance(date_input, str):
        date_input = datetime.fromisoformat(date_input)
    
    # Calculate the new date by adding months
    # First add the months to the year and month
    year = date_input.year + (date_input.month + months - 1) // 12
    month = (date_input.month + months - 1) % 12 + 1
    
    # Create date with same day in target month
    target_date = datetime(year, month, date_input.day)
    
    # Subtract 1 day
    result_date = target_date - timedelta(days=1)
    
    return result_date.strftime('%Y-%m-%d')


def combine_trend_files(directory, file_prefix):
    """
    Combines multiple CSV files with the same prefix into a single dataframe.
    
    Args:
        directory (str): Path to directory containing CSV files
        file_prefix (str): Prefix of files to combine
        
    Returns:
        pd.DataFrame: Combined dataframe with columns named by iteration
    """
    # Get all CSV files that start with the prefix
    files = [f for f in os.listdir(directory) 
             if f.startswith(file_prefix) and f.endswith('.csv')]

    # Sort files by their iteration number if they have that
    files.sort(key=lambda x: int(re.search(r'_i(\d+)\.csv$', x).group(1)))
    # print('Files after sorting by iteration number:')
    # print(files)

    files.sort()
    # print('Files after sorting by name:')
    # print(files)

    # Initialize an empty list to store dataframes
    dfs = []

    # Read each file and store in the list
    for i, file in enumerate(files):
        # Extract the iteration number from the filename
        # iter_num = re.search(r'_i(\d+)\.csv$', file).group(1)
        collected_at = re.search(r'_at_(.+?)(?:_i\d+)?\.csv$', file).group(1)
        collected_at = collected_at.rsplit('-', 1)[0] + ':' + collected_at.rsplit('-', 1)[1]
        collected_at = collected_at.replace('_at_', '')
        print(collected_at)
        # iter_num = i+1
        # Read the CSV file
        df = pd.read_csv(os.path.join(directory, file), index_col=0)
        # Rename the column to match the iteration number
        # df.columns = [f"i{iter_num}"]
        df.columns = [f"{collected_at}"]
        dfs.append(df)

    # Combine all dataframes horizontally
    combined_df = pd.concat(dfs, axis=1)
    
    return combined_df


def search_google_trends_staggered(
    search_term: str,
    start_date: Union[str, datetime],
    number_stagger: int,
    geo: Optional[str] = None,
    cat: Optional[str] = None,
    serpapi_api_key: Optional[str] = None,
    no_cache: bool = False,
    request_delay: Optional[int] = None,
    proxy: Optional[str] = None,
    change_identity: Optional[bool] = None,
) -> pd.DataFrame:
    """
    Perform staggered daily Google Trends searches starting from a given date.
    
    Args:
        search_term (str): The term to search for
        start_date (str): Initial start date in YYYY-MM-DD format
        number_stagger (int): Number of staggered searches to perform
        serpapi_api_key (str): API key for SerpAPI
        geo (str, optional): Geographic location. Defaults to "US"
        request_delay (int, optional): Delay between requests. Defaults to 2
        proxy (str, optional): Proxy server address. Defaults to "localhost:9050"
        change_identity (bool, optional): Whether to change Tor identity. Defaults to False
        tor_control_port (int, optional): Tor control port. Defaults to 9051
        tor_password (str, optional): Tor control password. Defaults to "your_tor_password"
        
    Returns:
        pd.DataFrame: Combined results from all staggered searches
    """
    all_results = []
    
    for i in range(number_stagger):
        # Calculate the staggered start date
        staggered_date = (datetime.fromisoformat(start_date) + timedelta(days=i)).strftime('%Y-%m-%d')
        
        # Perform the search for this staggered date
        result = search_google_trends_by_day(
            search_term=search_term,
            start_date=staggered_date,
            serpapi_api_key=serpapi_api_key,
            geo=geo,
            cat=cat,
            no_cache=no_cache,
            request_delay=request_delay,
            proxy=proxy,
            change_identity=change_identity
        )
        
        all_results.append(result)
    
    # Combine all results into a single DataFrame while preserving date index
    if all_results:
        combined_df = pd.concat(all_results, axis=1)
        # Rename columns to add sequential numbers
        combined_df.columns = [f"{col}_{i+1}" for i, col in enumerate(combined_df.columns)]
        return combined_df
    return pd.DataFrame()



def get_days_between_dates(start_date: datetime, end_date: datetime) -> int:
    """
    Calculate the number of full days between two datetime objects, rounding up to the nearest whole day.
    
    Args:
        start_date (datetime): The start date
        end_date (datetime): The end date
        
    Returns:
        int: Number of full days between the dates, rounded up
    """
    delta = end_date - start_date
    # Convert to days and round up using ceil
    days = math.ceil(delta.total_seconds() / (24 * 3600))
    return days

def get_number_of_90day_intervals(start_date: datetime, end_date: datetime) -> int:
    """
    Calculate the number of 90-day intervals between two dates, rounding up.
    
    Args:
        start_date (datetime): The start date
        end_date (datetime): The end date
        
    Returns:
        int: Number of 90-day intervals between the dates, rounded up
    """
    total_days = get_days_between_dates(start_date, end_date)
    # Calculate number of 90-day intervals and round up
    intervals = math.ceil(total_days / 90)
    return intervals




# Example usage
if __name__ == "__main__":
    print("This is a library, not a script. It is used to do google trends searches easily.")
    