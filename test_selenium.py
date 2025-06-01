from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth

import undetected_chromedriver as uc

from bs4 import BeautifulSoup
from urllib.parse import quote
from datetime import datetime
import time
import os
import sys
from typing import Optional, Callable

def change_identity(password: str = "your_password_here", print_func: Optional[Callable] = None) -> None:
    """
    Change the Tor identity by connecting to the Tor control port and sending a NEWNYM signal.
    Includes error handling and retry logic.
    
    Args:
        password (str): Password for Tor control port
        print_func (Optional[Callable]): Function to use for printing debug information
    """
    if print_func is None:
        print_func = print
        
    try:
        from stem.control import Controller
        from stem import Signal
    except ImportError:
        print_func("Error: stem library not installed. Please install it with 'pip install stem'")
        return

    try:
        # Try to connect to the Tor control port
        with Controller.from_port(port=9051) as controller:
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
        print_func("Add 'ControlPort 9051' to your torrc file and restart Tor.")

def setup_chrome_driver(testing: bool = True):
    """
    Set up ChromeDriver with proper error handling and Tor proxy configuration.
    Uses ChromeDriverManager to automatically download and manage the ChromeDriver.
    
    Args:
        testing (bool): If True, uses Chrome for Testing. If False, uses regular Chrome.
                       Defaults to True for better automation stability.
    """
    # Set up Chrome options
    chrome_options = Options()
    #chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Add Tor proxy configuration
    chrome_options.add_argument('--proxy-server=socks5://127.0.0.1:9150')
    
    # Additional options for stability
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Set Chrome binary location based on OS and testing preference
    if testing:
        if sys.platform == "darwin":  # macOS
            chrome_binary = "/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        elif sys.platform == "win32":  # Windows
            chrome_binary = "C:\\Program Files\\Google\\Chrome for Testing\\Application\\chrome.exe"
        elif sys.platform == "linux":  # Linux
            chrome_binary = "/usr/bin/google-chrome-for-testing"
        else:
            print("Warning: Unsupported operating system. Using default Chrome installation.")
            chrome_binary = None
        
        if chrome_binary and os.path.exists(chrome_binary):
            print(f"Using Chrome for Testing at: {chrome_binary}")
            chrome_options.binary_location = chrome_binary
        else:
            print("Warning: Chrome for Testing not found. Falling back to regular Chrome.")
            testing = False
    
    if not testing:
        print("Using regular Chrome installation.")
    
    try:
        # Use ChromeDriverManager to automatically download and manage ChromeDriver
        service = Service(ChromeDriverManager().install())
        
        # Initialize the Chrome driver with longer timeout
        # Use undetected_chromedriver to avoid detection
        driver = uc.Chrome(use_subprocess=False)
        # Use the regular webdriver.Chrome if you want to use the regular ChromeDriver
        #driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)  # Set page load timeout to 30 seconds
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")



        # # Selenium Stealth settings
        # stealth(driver,
        #     languages=["en-US", "en"],
        #     vendor="Google Inc.",
        #     platform="Win32",
        #     webgl_vendor="Intel Inc.",
        #     renderer="Intel Iris OpenGL Engine",
        #     fix_hairline=True,
        # )
        return driver
    except Exception as e:
        print(f"Error setting up ChromeDriver: {str(e)}")
        print("Make sure you have Chrome installed and that ChromeDriverManager can access the internet to download the appropriate driver.")
        sys.exit(1)
    
def parse_trends_page(driver: webdriver.Chrome) -> None:
    """
    Parse the Google Trends page source and extract table data using Selenium.
    If the table is not found, checks for rate limiting messages.
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
    """
    # Try Selenium search for the table
    print("\nSearching for trends data table...")
    try:
        table_element = driver.find_element(By.CSS_SELECTOR, 'div.line-chart-body-wrapper line-chart-directive div div div div div table tbody')
        print("Table found successfully!")
        print("Table contents:")
        print(table_element.get_attribute('outerHTML'))
    except Exception as e:
        print(f"Table search failed: {str(e)}")
        
        # Check for rate limiting messages
        print("\nChecking for rate limiting messages...")
        try:
            # Get all text content
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            # Look for rate limiting messages
            if "too many" in page_text:
                # Find the element containing the message
                elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'too many')]")
                
                if elements:
                    print("\nRate limiting message found:")
                    for element in elements:
                        # Get the text and its parent's text for context
                        message = element.text
                        parent_text = element.find_element(By.XPATH, "..").text
                        print(f"\nMessage: {message}")
                        print(f"Context: {parent_text}")
                else:
                    print("Rate limiting message found in page text but could not locate specific element.")
            else:
                print("No rate limiting messages found.")
                
        except Exception as e:
            print(f"Error checking for rate limiting messages: {str(e)}")
        
        # Print a sample of the page source for debugging
        print("\nPage source sample (first 1000 characters):")
        print(driver.page_source[:1000])

def parse_sannysoft_page(driver: webdriver.Chrome) -> None:
    """
    Parse the sannysoft bot detection page.
    Just prints the first 1000 characters of the page source.
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
    """
    page_source = driver.page_source
    print("\nPage source sample (first 1000 characters):")
    print(page_source[:1000])

def parse_scrapingcourse_page(driver: webdriver.Chrome) -> None:
    """
    Parse the scrapingcourse antibot challenge page.
    Looks for "bypassed" text to indicate successful challenge completion.
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
    """
    print("\nChecking for challenge completion...")
    try:
        # Get all text content
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        # Look for "bypassed" text
        if "bypassed" in page_text:
            # Find the element containing the message
            elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'bypassed')]")
            
            if elements:
                print("\nChallenge completed successfully!")
                for element in elements:
                    # Get the text and its parent's text for context
                    message = element.text
                    parent_text = element.find_element(By.XPATH, "..").text
                    print(f"\nMessage: {message}")
                    print(f"Context: {parent_text}")
            else:
                print("Found 'bypassed' in page text but could not locate specific element.")
        else:
            print("Challenge not completed - 'bypassed' text not found.")
            print("\nPage source sample (first 1000 characters):")
            print(driver.page_source[:1000])
            
    except Exception as e:
        print(f"Error checking challenge status: {str(e)}")
        print("\nPage source sample (first 1000 characters):")
        print(driver.page_source[:1000])

def test_chromedriver_call(
    search_terms: list = [],
    start_date: str = None,
    end_date: str = None,
    url: str = None,
    result_parser: Callable = parse_trends_page,
    testing: bool = True
):
    """
    Test a URL with ChromeDriver.
    
    Args:
        search_terms (list): List of search terms to query
        start_date (str): Start date in YYYY-MM-DD format (default: None for 'all')
        end_date (str): End date in YYYY-MM-DD format (default: None for 'all')
        url (str): URL template with {date_range} and {query} placeholders
        result_parser (Callable): Function to parse the page results
        testing (bool): Whether to use Chrome for Testing. If False, uses regular Chrome.
                       Defaults to True for better automation stability.
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
    
    # Construct the URL using format
    formatted_url = url.format(date_range=date_range, query=query)
    print(f"\nTesting URL: {formatted_url}")
    
    # Change Tor identity before making the request
    change_identity(password="controlpass")
    
    # Set up Chrome driver
    driver = setup_chrome_driver(testing=testing)
    
    # Load the page
    driver.get(formatted_url)
    
    # Wait for 5 seconds
    print("Waiting 10 seconds for page to load...")
    time.sleep(10)
    
    # Parse the page using the provided parser
    result_parser(driver)
    
    # Close the driver
    driver.quit()

if __name__ == "__main__":
    # Define test configurations
    test_configs = [
        {
            "name": "Sannysoft Bot Detection Test",
            "url": "https://bot.sannysoft.com/",
            "search_terms": [],
            "start_date": None,
            "end_date": None,
            "result_parser": parse_sannysoft_page,
            "testing": True
        },
        {
            "name": "ScrapingCourse Antibot Challenge Test",
            "url": "https://www.scrapingcourse.com/antibot-challenge",
            "search_terms": [],
            "start_date": None,
            "end_date": None,
            "result_parser": parse_scrapingcourse_page,
            "testing": False
        },
        {
            "name": "Google Trends Test",
            "url": "https://trends.google.com/trends/explore?date={date_range}&geo=US&q={query}&hl=en",
            "search_terms": ["car", "truck"],
            "start_date": "2024-04-30",
            "end_date": "2024-05-30",
            "result_parser": parse_trends_page,
            "testing": False
        }
    ]
    
    # Run each test configuration
    for config in test_configs:
        print(f"\n{'='*50}")
        print(f"Running {config['name']}")
        print(f"{'='*50}")
        
        test_chromedriver_call(
            search_terms=config["search_terms"],
            start_date=config["start_date"],
            end_date=config["end_date"],
            url=config["url"],
            result_parser=config["result_parser"],
            testing=config["testing"]
        )
