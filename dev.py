import requests
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from trendspy import Trends
import pandas as pd
from stem.control import Controller
from stem import Signal
import time
import socket
import os
import re

def change_tor_identity():
    """
    Change the Tor identity by connecting to the Tor control port and sending a NEWNYM signal.
    Includes error handling and retry logic.
    """
    try:
        # Try to connect to the Tor control port
        with Controller.from_port(port=9051) as controller:
            # Authenticate with the controller
            # If you have a password set in your torrc file, uncomment and use the line below
            controller.authenticate(password="controlpass")
            
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


def search_google_trends(
    query: Union[str, List[str]], 
    proxy: str = "localhost:9050",
    time_range: Optional[str] = None,
    geo: Optional[str] = None,
    cat: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search Google Trends for a given query using a specified proxy.
    
    Args:
        query (Union[str, List[str]]): The search term(s) to look up in Google Trends.
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
    
    Returns:
        Dict[str, Any]: The search results from Google Trends
    
    Raises:
        Exception: If there's an error with the trendspy request or proxy connection
    """
    try:
        # Configure the proxy for the request
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        
        request_delay = 2.0  # Add a delay between requests in seconds
        
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
        results = trends.interest_over_time(query, **params)
        
        return results
    
    except Exception as e:
        raise Exception(f"Error searching Google Trends: {str(e)}")

def multiple_search_trends(
    search_term: str, 
    time_range: str = "today 1-m", 
    n_iterations: int = 5,
    proxy: str = "localhost:9050",
    change_identity: bool = True,
    save_to_file: bool = True
) -> pd.DataFrame:
    """
    Perform multiple Google Trends searches for the same term and combine the results.
    
    Args:
        search_term (str): The search term to look up in Google Trends.
        time_range (str, optional): The time range for the search. Defaults to "today 1-m".
        n_iterations (int, optional): Number of times to perform the search. Defaults to 5.
        proxy (str, optional): The proxy to use. Defaults to "localhost:9050".
        change_identity (bool, optional): Whether to change Tor identity between iterations. Defaults to True.
        save_to_file (bool, optional): Whether to save the results to a CSV file. Defaults to True.
    
    Returns:
        pd.DataFrame: A dataframe containing all the timeseries data.
    """
    all_timeseries = []
    
    print(f"Collecting {n_iterations} timeseries for '{search_term}'...")
    
    for i in range(n_iterations):
        print(f"Iteration {i+1}/{n_iterations}")
        monthly_results = search_google_trends(search_term, time_range=time_range, proxy=proxy)
        print(f"\nShape: {monthly_results.shape}")
        all_timeseries.append(monthly_results)
        
        # Change Tor identity between iterations if requested
        if change_identity and i < n_iterations - 1:  # Don't change identity after the last iteration
            change_tor_identity()
            # Add a delay after changing identity to ensure it takes effect
            time.sleep(5)
    
    # Combine all timeseries into a single dataframe
    combined_df = pd.DataFrame()
    
    for i, df in enumerate(all_timeseries):
        # Drop the isPartial column if it exists
        if 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        
        # Add the data with simplified column names
        combined_df[f"iter_{i+1}"] = df[search_term]
    
    # Save the dataframe to a CSV file if requested
    if save_to_file:
        # Create a filename with the search term and current ISO date
        current_date = datetime.now().strftime("%Y-%m-%d")
        # Replace spaces with underscores in the search term for the filename
        safe_search_term = search_term.replace(" ", "_")
        filename = f"{safe_search_term}_{current_date}.csv"
        
        # Save the dataframe to the CSV file
        combined_df.to_csv(filename, index=True)
        print(f"\nData saved to {filename}")
    
    return combined_df

def numbered_file_name(orig_name: str, n_digits: int = 3) -> str:
    """
    Generate a numbered filename by incrementing the number at the end of the filename.
    If filename ends with _i### pattern, increment the number. If no number pattern exists,
    add _i### pattern with specified digits. Number of digits is enforced in both cases.
    
    Args:
        orig_name (str): The original filename.
        n_digits (int): Number of digits to use for the counter. Defaults to 3.
        
    Returns:
        str: New filename with incremented number or new _i### pattern.
    """
    # Split the filename into base name and extension
    base_name, ext = os.path.splitext(orig_name)
    
    # Check if filename ends with _i followed by any number of digits
    pattern = r'_i(\d+)$'
    match = re.search(pattern, base_name)
    
    if match:
        # Get the existing number and increment it
        number = int(match.group(1)) + 1
        # Remove existing _i and digits
        name = base_name[:match.start()]
    else:
        # No existing pattern, start with 1
        number = 1
        name = base_name
    
    # Create the new filename with _i and enforced n_digits pattern
    new_name = f"{name}_i{number:0{n_digits}d}{ext}"
    
    return new_name
    
# Example usage
if __name__ == "__main__":
    try:
        # Single search term
        search_term = "artificial intelligence"
        
        # Default time range
        time_range = "today 1-m"
        
        # Number of iterations
        n_iterations = 2
        
        # Use the multiple_search_trends function to collect and combine the data
        combined_df = multiple_search_trends(
            search_term=search_term,
            time_range=time_range,
            n_iterations=n_iterations
        )
        print("\nCombined timeseries dataframe:")
        print(combined_df.head())
        print(f"\nShape: {combined_df.shape}")


        
    except Exception as e:
        print(f"Error: {e}")
