from curl_cffi import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import quote
from datetime import datetime

def test_browser_impersonation():
    """
    Test browser impersonation using curl_cffi.
    This will make a request to tls.browserleaks.com to verify our browser fingerprint.
    """
    # Make request with Chrome impersonation
    r = requests.get("https://tls.browserleaks.com/json", impersonate="chrome")
    
    # Print the response
    print("\nChrome impersonation response:")
    print(json.dumps(r.json(), indent=2))
    
    # Make request with Firefox impersonation
    r = requests.get("https://tls.browserleaks.com/json", impersonate="firefox")
    
    # Print the response
    print("\nFirefox impersonation response:")
    print(json.dumps(r.json(), indent=2))
    
    # Make request with Safari impersonation
    r = requests.get("https://tls.browserleaks.com/json", impersonate="safari")
    
    # Print the response
    print("\nSafari impersonation response:")
    print(json.dumps(r.json(), indent=2))

def test_google_trends(
    search_terms: list,
    start_date: str = None,
    end_date: str = None,
    geo: str = "US",
    hl: str = "en"
):
    """
    Test Google Trends with multiple search terms.
    
    Args:
        search_terms (list): List of search terms to query
        start_date (str): Start date in YYYY-MM-DD format (default: None for 'all')
        end_date (str): End date in YYYY-MM-DD format (default: None for 'all')
        geo (str): Geographic location (default: "US")
        hl (str): Language (default: "en")
    """
    # Join search terms with commas and URL encode
    query = quote(",".join(search_terms))
    
    # Handle date range
    if start_date and end_date:
        # Validate date format
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
            date_range = quote(f"{start_date} {end_date}")
        except ValueError:
            print("Error: Dates must be in YYYY-MM-DD format")
            return
    else:
        date_range = "all"
    
    # Construct the URL
    url = f"https://trends.google.com/trends/explore?date={date_range}&geo={geo}&q={query}&hl={hl}"
    print(f"\nTesting URL: {url}")
    
    # Make request with Chrome impersonation
    r = requests.get(url, impersonate="chrome")
    
    # Parse the HTML response
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Find the table using the specified selector
    table = soup.select_one('div.line-chart-body-wrapper line-chart-directive div div div div div table tbody')
    
    if table:
        print("\nFound table data:")
        # Print the table contents
        print(table.prettify())
    else:
        print("\nTable not found in response")
        # Print a sample of the response for debugging
        print("\nResponse sample:")
        print(r.text[:1000])  # First 1000 characters

if __name__ == "__main__":
    # Test browser impersonation
    #test_browser_impersonation()
    
    # Test Google Trends with some example search terms and date range
    test_google_trends(
        search_terms=["car", "truck"],
        start_date="2024-04-30",
        end_date="2024-05-30"
    ) 