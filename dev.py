#! /opt/miniconda3/envs/trendspy/bin/python3

from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import os
from enum import Enum
import gtrend_tools
import time
import compress_pickle
import sys
sys.exit()
class SearchMethod(Enum):
    TRENDSPY_LOCAL = "trendspy_local"
    TRENDSPY_TOR = "trendspy_tor" 
    SERPAPI = "serpapi"

def collect_and_save_trends(
    search_term: str,
    time_range: str,
    n_iterations: int,
    search_method: SearchMethod = SearchMethod.SERPAPI,
    serpapi_api_key: Optional[str] = None,
    proxy: Optional[str] = None,
    change_identity: bool = False,
    request_delay: int = 60,
    save_path: str = "/Users/dperlman/Documents/git/trendICA/testdata",
    no_cache: bool = False
) -> dict:
    """
    Collect Google Trends data and save it to both CSV and pickle formats.
    
    Args:
        search_term (str): The term to search for
        time_range (str): Time range for the search
        n_iterations (int): Number of iterations to perform
        search_method (SearchMethod): Method to use for searching (TRENDSPY_LOCAL, TRENDSPY_TOR, or SERPAPI)
        serpapi_api_key (Optional[str]): API key for SerpAPI
        proxy (Optional[str]): Proxy server address
        change_identity (bool): Whether to change Tor identity
        request_delay (int): Delay between requests in seconds
        save_path (str): Path to save the output files
        no_cache (bool): Whether to disable caching of results
        
    Returns:
        dict: Dictionary containing:
            - n: Number of search requests performed
            - csv: Full path to the saved CSV file
            - cumulative: Full path to the saved cumulative file
    """
    start_time = time.time()
    
    # Configure search parameters based on method
    if search_method == SearchMethod.TRENDSPY_TOR:
        proxy = "localhost:9050"
        change_identity = True
        serpapi_api_key = None
    elif search_method == SearchMethod.TRENDSPY_LOCAL:
        proxy = None
        change_identity = False
        serpapi_api_key = None
    elif search_method == SearchMethod.SERPAPI:
        proxy = None
        change_identity = False
        serpapi_api_key = "76f3ea1f6758054f7bb79457102d937bc1dff7ae4a1ecc98e6a5751530a11824"

    # Collect the data
    combined_df = gtrend_tools.search_google_trends(
        search_term=search_term,
        time_range=time_range,
        n_iterations=n_iterations,
        serpapi_api_key=serpapi_api_key,
        proxy=proxy,
        change_identity=change_identity,
        request_delay=request_delay,
        no_cache=no_cache
    )

    safe_search_term = search_term.replace(" ", "_")
    safe_time_range = time_range.replace(" ", "--")
    filename_root = f"{safe_search_term}_{safe_time_range}"

    # Calculate execution time
    execution_time = time.time() - start_time
    execution_comment = f"Execution time: {execution_time:.2f} seconds"

    # Save to CSV
    csv_filename = gtrend_tools.save_to_csv(combined_df, filename_root, path=save_path, comment=execution_comment)
    csv_path = os.path.join(save_path, csv_filename)

    # Combine the files
    combined_df = gtrend_tools.combine_trend_files(save_path, filename_root)

    # Save as pickle
    combined_file_name = f"{filename_root}_cumulative.gz"
    cumulative_path = os.path.join(save_path, combined_file_name)
    combined_df.to_pickle(cumulative_path)

    return {
        "n": n_iterations,
        "csv": csv_path,
        "cumulative": cumulative_path
    }



# Example usage
if __name__ == "__main__":
    start_time = time.time()

    # log file
    log_file = "/Users/dperlman/Documents/git/trendICA/testdata/log.txt"
    with open(log_file, "a") as f:
        f.write(f"Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Number of iterations
    n_iterations = 1
    
    # Request delay
    request_delay = 60
    
    # No cache
    no_cache = True
    
    # Search terms and time ranges
    searches = [
        {
            "term": "artificial intelligence",
            "time_range": "2024-01-01 2025-04-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata"
        },
        {
            "term": "bathroom bill",
            "time_range": "2008-01-01 2024-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata"
        },
        {
            "term": "transgender",
            "time_range": "2008-01-01 2024-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata"
        },
        {
            "term": "qanon",
            "time_range": "2018-01-01 2024-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata"
        },
        # now start doing the repeat searches over time for artificial intelligence
        {
            "term": "artificial intelligence",
            "time_range": "2025-01-01 2025-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2024-10-01 2024-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2024-07-01 2024-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2024-04-01 2024-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2024-01-01 2024-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2023-10-01 2023-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2023-07-01 2023-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2023-04-01 2023-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2023-01-01 2023-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2022-10-01 2022-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2022-07-01 2022-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2022-04-01 2022-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2022-01-01 2022-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2021-10-01 2021-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2021-07-01 2021-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2021-04-01 2021-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2021-01-01 2021-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2020-10-01 2020-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2020-07-01 2020-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2020-04-01 2020-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        {
            "term": "artificial intelligence",
            "time_range": "2020-01-01 2020-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/artificial_intelligence"
        },
        # now start doing the repeat searches over time for qanon
        {
            "term": "qanon",
            "time_range": "2025-01-01 2025-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2024-10-01 2024-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2024-07-01 2024-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2024-04-01 2024-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2024-01-01 2024-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2023-10-01 2023-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2023-07-01 2023-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2023-04-01 2023-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2023-01-01 2023-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2022-10-01 2022-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2022-07-01 2022-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2022-04-01 2022-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2022-01-01 2022-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2021-10-01 2021-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2021-07-01 2021-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2021-04-01 2021-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2021-01-01 2021-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2020-10-01 2020-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2020-07-01 2020-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2020-04-01 2020-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2020-01-01 2020-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2019-10-01 2019-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2019-07-01 2019-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2019-04-01 2019-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2019-01-01 2019-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2018-10-01 2018-12-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2018-07-01 2018-09-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2018-04-01 2018-06-30",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        },
        {
            "term": "qanon",
            "time_range": "2018-01-01 2018-03-31",
            "save_path": "/Users/dperlman/Documents/git/trendICA/testdata/qanon"
        }

    ]
    
    # Process each search
    total_searches = 0
    for search in searches:
        result = collect_and_save_trends(
            search_term=search["term"],
            time_range=search["time_range"],
            n_iterations=n_iterations,
            search_method=SearchMethod.SERPAPI,
            request_delay=request_delay,
            save_path=search["save_path"],
            no_cache=no_cache
        )
        total_searches += result['n']
        with open(log_file, "a") as f:
            f.write(f"Wrote file {result['csv']}\n")
            f.write(f"Wrote cumulative file {result['cumulative']}\n")
    
    end_time = time.time()
    execution_time = end_time - start_time
    with open(log_file, "a") as f:
        f.write(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total execution time: {execution_time:.2f} seconds\n")
        f.write(f"Performed {total_searches} total searches for {len(searches)} search terms\n\n")


    # done for now, don't start the stagger searches just yet.
    sys.exit()

    # now use search_google_trends_by_day to get the trends by day
    
    # terms to search
    # search_terms = [
    #     "artificial intelligence",
    #     "qanon",
    #     "bathroom bill",
    #     "transgender",
    #     "birther",
    #     "obama birth certificate",
    #     "adrenochrome",
    #     "do your own research",
    #     "great awakening"
    # ]
    search_terms = [
        "bathroom bill",
        "transgender"
    ]
    
    # time range
    start_date = "2008-01-01"
    end_date = "2024-12-31"
    
    # Set the output path
    stagger_path = "./testdata/staggers"
    
    # Create directory if it doesn't exist
    os.makedirs(stagger_path, exist_ok=True)

    # Set up logging
    stagger_log_file = os.path.join(stagger_path, "log.txt")
    with open(stagger_log_file, "a") as f:
        f.write(f"Starting stagger searches at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Process each search term
    for term in search_terms:
        term_start_time = time.time()
        print(f"Processing {term}...")
        
        # Get the trends data
        result = gtrend_tools.search_google_trends_by_day(
            search_term=term,
            start_date=start_date,
            end_date=end_date,
            stagger=1,  # Use 50% overlap
            raw_groups=True  # Get the raw stagger groups
        )
        
        # Create safe filename
        safe_term = term.replace(" ", "_")
        formatted_utc_gmtime = time.strftime("%Y-%m-%dT%H-%MUTC", time.gmtime())
        filename = f"{safe_term}_at_{formatted_utc_gmtime}_stagger_groups.gz"

        filepath = os.path.join(stagger_path, filename)
        
        # Save using compress_pickle
        compress_pickle.dump(result, filepath)
            
        print(f"Saved stagger groups for {term} to {filepath}")
        
        # Log completion of this term
        term_execution_time = time.time() - term_start_time
        with open(stagger_log_file, "a") as f:
            f.write(f"Completed {term} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Execution time: {term_execution_time:.2f} seconds\n")

    # Log overall completion
    with open(stagger_log_file, "a") as f:
        f.write(f"Finished all stagger searches at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
