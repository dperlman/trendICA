import applescript
from urllib.parse import quote
from datetime import datetime
import time
import sys
from typing import Optional, Callable, List, Dict, Any, Union
import rjsmin
import html
from bs4 import BeautifulSoup
from .base_classes import API_Call
import pandas as pd
from utils import _print_if_verbose

# Constants
WAIT_TIME = 10

# Global search terms by name
CONFIRM_CONFIGS = {
    'google_auth': {
        'url': 'https://accounts.google.com',
        'terms': [
            {'term': 'Welcome', 'queryselector': None},
            {'term': 'Personal info', 'queryselector': None},
            {'term': 'Data & privacy', 'queryselector': None},
        ]
    },
    'google_trends': {
        'url': 'https://trends.google.com/trends/explore?date={date_range}&geo={geo}&q={query}&hl=en',
        'terms': [
            {'term': 'Interest over time', 'queryselector': 'div.fe-line-chart-header-title'},
            {'term': 'Trending Now', 'queryselector': 'a.tab-title'},
            # Add more terms here as needed
        ]
    }
}

class ApplescriptSafari(API_Call):
    def __init__(
        self,
        **kwargs
    ):
        """
        Initialize the ApplescriptSafari class.
        
        Args:
            **kwargs: Additional keyword arguments passed to API_Call
        """
        super().__init__(**kwargs)

    def search(
        self,
        search_term: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> 'ApplescriptSafari':
        """
        Search Google Trends using Safari and AppleScript.
        
        Args:
            search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
            start_date (Optional[Union[str, datetime]]): Start date for the search
            end_date (Optional[Union[str, datetime]]): End date for the search
            
        Returns:
            ApplescriptSafari: Returns self for method chaining
        """
        # Store search specification
        self.search_spec = {
            'terms': search_term,
            'start_date': start_date,
            'end_date': end_date,
            'geo': self.geo,
            'language': self.language
        }
        
        self.print_func(f"Sending ApplescriptSafari search request:")
        self.print_func(f"  Search term: {search_term}")
        self.print_func(f"  Start date: {start_date if start_date else 'default'}")
        self.print_func(f"  End date: {end_date if end_date else 'default'}")
        
        try:
            # Check Google authentication first
            if not get_google_auth(print_func=self.print_func):
                raise Exception("Google authentication check failed")
            
            # Construct the URL
            config = CONFIRM_CONFIGS['google_trends']
            url_template = config['url']
            
            # Join search terms with commas and URL encode
            query = quote(",".join(search_term if isinstance(search_term, list) else [search_term]))
            self.print_func(f"Query: {query}")
            
            # Handle date range
            if start_date and end_date:
                # Validate date format
                try:
                    datetime.strptime(start_date, "%Y-%m-%d")
                    datetime.strptime(end_date, "%Y-%m-%d")
                    date_range = quote(f"{start_date} {end_date}")
                    self.print_func(f"Encoded date range: {date_range}")
                except ValueError:
                    raise ValueError("Dates must be in YYYY-MM-DD format")
            else:
                date_range = "all"
                self.print_func("Using default date range: all")
            
            # Construct the URL
            formatted_url = url_template.format(date_range=date_range, query=query, geo=self.geo)
            self.print_func(f"\nOpening URL: {formatted_url}")
            
            # Open URL in Safari
            open_url_in_safari(formatted_url, print_func=self.print_func)
            
            # Get the raw HTML from the trends page
            html_content = parse_trends_page(print_func=self.print_func)
            if not html_content:
                raise Exception("Failed to parse trends page")
            
            # Store the raw HTML data
            self.raw_data = html_content
            
            self.print_func("  Search successful!")
            return self
                    
        except Exception as e:
            self.print_func(f"  Search failed: {str(e)}")
            raise

    def standardize_data(self) -> 'ApplescriptSafari':
        """
        Standardize the raw HTML data into a common format.
        Parses the HTML table into a list of dictionaries with date and values.
        
        Returns:
            ApplescriptSafari: Returns self for method chaining
        """
        if not self._raw_data_history:
            raise ValueError("No raw data available. Call search() first.")
            
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(self._raw_data_history[-1], 'html.parser')
        
        # Find the table
        table = soup.find('table')
        if not table:
            raise ValueError("No table found in HTML data")
            
        # Get headers (column names)
        headers = [th.text.strip() for th in table.find_all('th')]
        if not headers:
            raise ValueError("No headers found in table")
            
        # The first column should be 'x' (dates)
        if headers[0] != 'x':
            raise ValueError("First column is not 'x' (dates)")
            
        # Get all rows
        rows = table.find_all('tr')[1:]  # Skip header row
        
        # Get search terms from search_spec
        search_terms = self.search_spec['terms']
        if not isinstance(search_terms, list):
            search_terms = [search_terms]
            
        # Transform the data into the standardized format
        standardized_data = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) != len(headers):
                continue  # Skip malformed rows
                
            # Parse the date
            date_str = cells[0].text.strip()
            try:
                # Remove any special characters and parse the date
                date_str = date_str.replace('\u202a', '').replace('\u202c', '')  # Remove LTR/RTL marks
                date = datetime.strptime(date_str, '%b %d, %Y')
            except ValueError:
                continue  # Skip rows with invalid dates
                
            # Get values for each column (except the date column)
            values = []
            for i, cell in enumerate(cells[1:], 1):
                try:
                    value = int(cell.text.strip())
                    # Use the search term from search_spec
                    search_term = search_terms[i-1] if i-1 < len(search_terms) else f"term_{i}"
                    values.append({
                        'value': value,
                        'query': search_term
                    })
                except ValueError:
                    continue  # Skip invalid values
                    
            if values:  # Only add entries that have valid values
                standardized_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'values': values
                })
        
        if not standardized_data:
            raise ValueError("No valid data found in table")
            
        self._data_history.append(standardized_data)
        return self

def dummy_print(*args, **kwargs) -> None:
    """A dummy print function that does nothing."""
    pass

def limited_print(text: str, limit: int = 1000) -> None:
    """Print a string with a maximum length."""
    text_str = str(text)[:limit]
    if len(str(text)) > limit:
        text_str += "..."
    print(text_str)

def create_safari_window(url: Optional[str] = None, print_func: Optional[Callable] = None) -> None:
    """
    Create a new Safari window using AppleScript.
    
    Args:
        url (Optional[str]): URL to open in the new window. If None, opens an empty window.
        print_func (Optional[Callable]): Function to use for printing debug information
    """
    print_func = print_func or _print_if_verbose
        
    try:
        # AppleScript to create new window
        if url:
            script = f'''
            tell application "Safari"
                activate
                make new document with properties {{URL:"{url}"}}
            end tell
            '''
        else:
            script = '''
            tell application "Safari"
                activate
                make new document
            end tell
            '''
        
        # Run the AppleScript
        result = applescript.run(script)
        
        if result.code == 0:
            if url:
                print_func(f"Successfully created new Safari window with URL: {url}")
            else:
                print_func("Successfully created new Safari window")
        else:
            print_func(f"Error creating Safari window: {result.err}")
            
    except Exception as e:
        print_func(f"Error executing AppleScript: {str(e)}")

def get_escaped_js_for_text_search_v1(search_text: str) -> str:
    """
    Generate escaped JavaScript code to find leaf elements containing the given text.
    
    Args:
        search_text (str): The text to search for in elements
        
    Returns:
        str: Escaped JavaScript code ready to be used in AppleScript
    """
    js_code = f'''
    (function() {{
        try {{
            const searchText = '{search_text}'.normalize();
            console.debug('Debugging info for test_applescript_safari.py. Search text: ' + searchText);
            
            // Get all elements
            const elements = Array.from(document.querySelectorAll('*'));
            console.debug('Debugging info for test_applescript_safari.py. Total elements: ' + elements.length);
            
            // Filter to leaf elements
            const leafElements = elements.filter(el => el.children.length === 0);
            console.debug('Debugging info for test_applescript_safari.py. Leaf elements: ' + leafElements.length);
            
            // First try text match in regular elements (non-script)
            const matches = leafElements
                .filter(el => el.tagName !== 'SCRIPT' && el.textContent.normalize().includes(searchText));
            console.debug('Debugging info for test_applescript_safari.py. Text matches: ' + matches.length);
            
            if (matches.length > 0) {{
                return JSON.stringify(matches.map(el => ({{
                    text: el.textContent.trim(),
                    tag: el.tagName,
                    matchType: 'text',
                    outerHTML: el.outerHTML
                }})));
            }}
            
            // If no matches in regular elements, try script elements
            const scriptElements = leafElements
                .filter(el => el.tagName === 'SCRIPT' && el.textContent.normalize().includes(searchText));
            console.debug('Debugging info for test_applescript_safari.py. Script matches: ' + scriptElements.length);
            
            if (scriptElements.length > 0) {{
                return JSON.stringify(scriptElements.map(el => ({{
                    text: el.textContent.trim(),
                    tag: el.tagName,
                    matchType: 'script',
                    outerHTML: el.outerHTML
                }})));
            }}
            
            // If still no matches, return debug info
            return JSON.stringify({{
                matchType: 'debug',
                fullSource: document.documentElement.outerHTML,
                elementCount: elements.length,
                leafElementCount: leafElements.length
            }});
        }} catch (error) {{
            console.debug('JavaScript Error in test_applescript_safari.py:');
            console.debug('Error message:', error.toString());
            console.debug('Stack trace:', error.stack);
            return JSON.stringify({{
                matchType: 'error',
                error: error.toString(),
                stack: error.stack
            }});
        }}
    }})();
    '''
    # First minimize the JavaScript
    minified_js = rjsmin.jsmin(js_code)
    # Then escape quotes and newlines for AppleScript
    return minified_js.replace('"', '\\"').replace('\n', ' ')

def get_escaped_js_for_text_search_v2(search_text: str, query_selector: str, print_func: Optional[Callable] = None) -> str:
    """
    Generate escaped JavaScript code to find elements matching the query selector that contain the given text.
    Recursively searches through child elements to find leaf nodes containing the text.
    
    Args:
        search_text (str): The text to search for in elements
        query_selector (str): CSS query selector to narrow down the search
        
    Returns:
        str: Escaped JavaScript code ready to be used in AppleScript
    """
    print_func = print_func or _print_if_verbose
    print_func(f"V2 search Query selector: {query_selector}")
    js_code = f'''
    (function() {{
        try {{
            const searchText = '{search_text}'.normalize('NFKC').trim();
            const querySelector = '{query_selector}';
            
            // Helper to get CSS selector string for an element
            function getCssSelector(el) {{
                let selector = el.tagName.toLowerCase();
                if (el.id) selector += '#' + el.id;
                if (el.className && el.className.trim()) {{
                    // Split class names and remove empty strings
                    const classes = el.className.trim().split(' ').filter(className => className !== '');
                    if (classes.length > 0) {{
                        selector += '.' + classes.join('.');
                    }}
                }}
                return selector;
            }}
            
            // First get elements matching the query selector
            const elements = Array.from(document.querySelectorAll(querySelector));
            console.debug('Debugging test_applescript_safari.py. Query selector matches:');
            console.debug(querySelector);
            console.debug(elements);
            
            // Function to recursively find leaf elements containing the text
            function findLeafElementsWithText(element) {{
                const normalizedText = element.textContent.normalize('NFKC').trim();
                
                if (normalizedText.includes(searchText)) {{
                    console.debug('Found matching text "' + searchText + '" in element: ' + getCssSelector(element));
                    return [element];
                }}
                
                // If it has children, recursively check each child
                let results = [];
                for (const child of element.children) {{
                    const childResults = findLeafElementsWithText(child);
                    if (childResults.length > 0) {{
                        results = results.concat(childResults);
                    }}
                }}
                return results;
            }}
            
            // Find all leaf elements containing the text
            const leafElements = elements.flatMap(el => findLeafElementsWithText(el));
                
            console.debug('searchText: ' + searchText + ' Text matches:');
            console.debug(leafElements);
            
            if (leafElements.length > 0) {{
                return JSON.stringify(leafElements.map(el => ({{
                    text: el.textContent.trim(),
                    tag: el.tagName,
                    matchType: 'text',
                    selector: querySelector,
                    cssSelector: getCssSelector(el),
                    outerHTML: el.outerHTML
                }})));
            }}
            
            // If no matches, return debug info
            return JSON.stringify({{
                matchType: 'debug',
                fullSource: document.documentElement.outerHTML,
                querySelector: querySelector,
                elementCount: elements.length
            }});
        }} catch (error) {{
            console.debug('JavaScript Error in test_applescript_safari.py:');
            console.debug('Error message:', error.toString());
            console.debug('Stack trace:', error.stack);
            // Return empty array to indicate no matches
            return '[]';
        }}
    }})();
    '''
    # First minimize the JavaScript
    minified_js = rjsmin.jsmin(js_code)
    # Then escape quotes and newlines for AppleScript
    return minified_js.replace('"', '\\"').replace('\n', ' ')

def get_element_by_text(search_text: str, query_selector: Optional[str] = None, print_func: Optional[Callable] = None) -> List[Dict[str, str]]:
    """
    Find leaf elements containing the given text in the current Safari tab.
    
    Args:
        search_text (str): The text to search for in elements
        query_selector (Optional[str]): CSS query selector to narrow down the search. If None, searches all elements.
        print_func (Optional[Callable]): Function to use for printing debug information
        
    Returns:
        List[Dict[str, str]]: List of dictionaries containing tag and text for each matching element.
        Only returns elements with matchType 'text' or 'script'. Returns empty list if only debug data found.
    """
    print_func = print_func or _print_if_verbose
    
    # Get escaped JavaScript code for finding the text
    if query_selector is None:
        print_func(f"V1 search text: {search_text}")
        escaped_js = get_escaped_js_for_text_search_v1(search_text)
    else:
        print_func(f"V2 search text: {search_text}")
        print_func(f"V2 search Query selector: {query_selector}")
        escaped_js = get_escaped_js_for_text_search_v2(search_text, query_selector)
    
    # Execute JavaScript - note that escaped_js is already escaped, so we don't need to escape it again
    script = f'''
    tell application "Safari"
        tell front window
            tell current tab
                do JavaScript "{escaped_js}"
            end tell
        end tell
    end tell
    '''
    
    result = applescript.run(script)

    if result.code == 0 and result.out:
        import json
        data = json.loads(result.out)
        
        # Handle debug case
        if isinstance(data, dict) and data.get('matchType') == 'debug':
            print_func("Debug data found:")
            print_func(f"Full source length: {len(data.get('fullSource', ''))}")
            if query_selector:
                print_func(f"Query selector: {data.get('querySelector', 'unknown')}")
                print_func(f"Elements found: {data.get('elementCount', 0)}")
            return data
        
        # Handle list of matches case
        if isinstance(data, list):
            # Filter out debug data first
            actual_matches = [elem for elem in data if elem.get('matchType') in ['text', 'script']]
            
            if actual_matches:
                print_func(f"Found elements containing '{search_text}':")
                for elem in actual_matches:
                    match_type = elem.get('matchType', 'unknown')
                    print_func(f"Match type: {match_type}")
                    print_func(f"Tag: {elem['tag']}")
                    if query_selector:
                        print_func(f"Selector: {elem.get('selector', 'unknown')}")
                    
                    # Get context around the match
                    text = elem['text']
                    match_index = text.lower().find(search_text.lower())
                    if match_index != -1:
                        start = max(0, match_index - 100)
                        end = min(len(text), match_index + len(search_text) + 100)
                        context = text[start:end]
                        if start > 0:
                            context = "..." + context
                        if end < len(text):
                            context = context + "..."
                        # used this for debugging
                        # print_func(f"Text context: {context}")
                    else:
                        print_func(f"Text: {text}")
                    
                    print_func("-" * 40)
            return actual_matches
        
        return []
    else:
        print_func("JavaScript execution failed or returned no output")
        if result.err:
            print_func(f"AppleScript error: {result.err}")
        return []

def poll_for_text(search_text: str, max_tries: int = 10, wait_time: int = 1, print_func: Optional[Callable] = None, query_selector: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Poll for text in the current Safari tab.
    
    Args:
        search_text (str): The text to search for
        max_tries (int): Maximum number of polling attempts
        wait_time (int): Time to wait between attempts in seconds
        print_func (Optional[Callable]): Function to use for printing debug information
        query_selector (Optional[str]): CSS query selector to narrow down the search
        
    Returns:
        List[Dict[str, str]]: List of matching elements if found, empty list if not found
    """
    print_func = print_func or _print_if_verbose
    
    last_debug_source = None
    for attempt in range(max_tries):
        if max_tries > 1:
            print_func(f"--Polling attempt {attempt + 1}/{max_tries} for '{search_text}'")
        else:
            print_func(f"--Checking for '{search_text}'")
        elements = get_element_by_text(search_text, query_selector=query_selector, print_func=print_func)
        
        # Check if we got debug data back
        if isinstance(elements, dict) and elements.get('matchType') == 'debug':
            last_debug_source = elements.get('fullSource')
        
        if elements and not isinstance(elements, dict):  # Only return if we have actual matches
            return elements
            
        if attempt < max_tries - 1:  # Don't sleep on the last attempt
            time.sleep(wait_time)
    
    # If we have debug source from the last attempt, save it to a file
    if last_debug_source:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_text = search_text.replace(' ', '_')
        filename = f"debug_source_{safe_text}_{timestamp}.html"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(last_debug_source)
            print_func(f"\nSaved debug source to {filename}")
        except Exception as e:
            print_func(f"Error saving debug source: {str(e)}")
    
    return []

def confirm_page(confirm_terms: list, print_func: Optional[Callable] = None, max_tries: int = 1, wait_time: int = 0) -> Dict[str, Any]:
    """
    Confirm the presence of specific texts on the current page using provided query selectors.
    
    Args:
        confirm_terms (list): List of dicts, each with 'term' and 'queryselector'
        print_func (Optional[Callable]): Function to use for printing debug information
        max_tries (int): Maximum number of polling attempts for each text
        wait_time (int): Time to wait between attempts in seconds
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - all: bool indicating if all terms were found
            - some: bool indicating if any terms were found
            - found: list of terms that were found
            - missing: list of terms that were not found
            - found_html: list of HTML strings for each found term
    """
    print_func = print_func or _print_if_verbose
    
    missing_confirms = []
    found_confirms = []
    found_confirms_html = []
    for confirm in confirm_terms:
        confirm_text = confirm['term']
        query_selector = confirm.get('queryselector', None)
        print_func("="*50)
        elements = poll_for_text(confirm_text, max_tries=max_tries, wait_time=wait_time, print_func=print_func, query_selector=query_selector)
        if elements:
            print_func(f"Confirmed presence of '{confirm_text}'")
            found_confirms.append(confirm_text)
            found_confirms_html.append(elements[-1]['outerHTML'])
        else:
            missing_confirms.append(confirm_text)
    
    if missing_confirms:
        print_func("\n" + "="*50)
        print_func("Warning: not all confirmation strings found!")
        print_func(f"Missing confirms: {missing_confirms}")
        print_func("="*50)
    
    if found_confirms:
        print_func("\n" + "="*50)
        print_func("Found confirms:")
        print_func(found_confirms)
        print_func("="*50)
    
    return {
        'all': len(missing_confirms) == 0,
        'some': len(found_confirms) > 0,
        'found': found_confirms,
        'missing': missing_confirms,
        'found_html': found_confirms_html
    }

def get_google_auth(
    poll_max_tries: int = 10,
    poll_wait_time: int = 1,
    print_func: Optional[Callable] = None
) -> Optional[str]:
    """
    Check Google authentication status by opening accounts.google.com and looking for specific elements.
    Uses polling to check for the presence of poll_text and then confirms with additional text checks.
    
    Args:
        poll_max_tries (int): Maximum number of polling attempts for initial text
        poll_wait_time (int): Time to wait between polling attempts in seconds
        print_func (Optional[Callable]): Function to use for printing debug information
        
    Returns:
        Optional[str]: 'confirmed' if all checks pass, 'unconfirmed' if poll_text found but confirm_texts missing,
                      None if poll_text not found
    """
    print_func = print_func or _print_if_verbose
    
    confirm_config = CONFIRM_CONFIGS['google_auth']
    url = confirm_config['url']
    terms = confirm_config['terms']
    
    print_func("\n" + "="*50)
    print_func("Starting Google authentication check")
    print_func("="*50)
    
    # Open Google account page in a new window
    create_safari_window(url=f"{url}", print_func=print_func)
    
    # Poll for initial text (first term)
    initial_term = terms[0]
    elements = poll_for_text(initial_term['term'], max_tries=poll_max_tries, wait_time=poll_wait_time, print_func=print_func, query_selector=initial_term.get('queryselector'))
    if not elements:
        print_func(f"No '{initial_term['term']}' text found after all attempts")
        return None
        
    print_func(f"Successfully found '{initial_term['term']}' text")
    
    # Check for confirmation texts (all terms)
    if confirm_page(confirm_terms=terms[1:], print_func=print_func):
        return 'confirmed'
    return 'unconfirmed'

def open_url_in_safari(url: str, print_func: Optional[Callable] = None) -> None:
    """
    Open a URL in the current Safari window using AppleScript.
    
    Args:
        url (str): The URL to open
        print_func (Optional[Callable]): Function to use for printing debug information
    """
    print_func = print_func or _print_if_verbose
    
    try:
        print_func(f"Preparing to open URL: {url}")
        # AppleScript to open URL in new tab and set it as current tab
        script = f'''
        tell application "Safari"
            if (count of windows) = 0 then
                make new document with properties {{URL:"{url}"}}
            else
                tell front window
                    set newTab to make new tab with properties {{URL:"{url}"}}
                    set current tab to newTab
                end tell
            end if
        end tell
        '''
        print_func("Executing AppleScript...")
        
        # Run the AppleScript
        result = applescript.run(script)
        
        if result.code == 0:
            print_func(f"Successfully opened URL: {url}")
        else:
            print_func(f"Error opening URL: {result.err}")
            print_func(f"Error code: {result.code}")
            
    except Exception as e:
        print_func(f"Error executing AppleScript: {str(e)}")
        print_func(f"Error type: {type(e)}")

def parse_trends_page(print_func: Optional[Callable] = None) -> str:
    """
    Parse the Google Trends page using confirm_page to check for expected elements.
    Uses a predefined set of terms to verify the page has loaded correctly.
    
    Args:
        print_func (Optional[Callable]): Function to use for printing debug information
        
    Returns:
        str: Prettified HTML of the y1 element if found, empty string if not found
    """
    print_func = print_func or _print_if_verbose
    # This may need to be changed if Google changes the Trends page, which they often do, to stop us from doing exactly this.
    confirm_selector = 'div.line-chart-body-wrapper line-chart-directive div div div div div table'
    confirm_terms = ['x', 'y1', 'y2']
    data_term = 'y1'
    
    # Create confirmation terms for each search term
    confirm_terms = [
        {'term': term, 'queryselector': confirm_selector} 
        for term in confirm_terms
    ]
    
    # Add the "Trending Now" term
    confirm_terms.append({'term': 'Trending Now', 'queryselector': 'a.tab-title'})
    
    print_func("\nChecking for expected elements on trends page...")
    result = confirm_page(confirm_terms=confirm_terms, print_func=print_func, max_tries=3, wait_time=2)
    
    if not result['all']:
        print_func("Warning: Some expected elements were not found on the page")
        if result['some']:
            print_func(f"Found elements: {result['found']}")
        print_func(f"Missing elements: {result['missing']}")
        return ""
    else:
        print_func("Successfully found all expected elements")
        print_func(f"Found elements: {result['found']}")
        
        # Get the y1 element and print its outerHTML
        print_func("\nGetting y1 element HTML...")
        y1_elements = get_element_by_text(data_term, query_selector=confirm_selector, print_func=print_func)
        if y1_elements:
            print_func("Found y1 element outerHTML.")
            html_content = y1_elements[0]['outerHTML']
            # Prettify the HTML using BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            prettified_html = soup.prettify()
            return prettified_html
        else:
            print_func("Could not find y1 element")
            return ""

def trends_applescript_safari(
    search_terms: List[str] = [],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    result_parser: Callable = None,
    print_func: Optional[Callable] = None
) -> None:
    """
    Test a URL with Safari using AppleScript.
    
    Args:
        search_terms (List[str]): List of search terms to query
        start_date (Optional[str]): Start date in YYYY-MM-DD format
        end_date (Optional[str]): End date in YYYY-MM-DD format
        result_parser (Callable): Function to parse the page results
        print_func (Optional[Callable]): Function to use for printing debug information
    """
    print_func = print_func or _print_if_verbose
    
    config = CONFIRM_CONFIGS['google_trends']
    url_template = config['url']
    
    print_func("\nStarting trends_applescript_safari")
    print_func(f"Search terms: {search_terms}")
    print_func(f"Date range: {start_date} to {end_date}")
    print_func(f"URL template: {url_template}")
    
    # Join search terms with commas and URL encode
    query = quote(",".join(search_terms))
    print_func(f"Encoded query: {query}")
    
    # Handle date range
    if start_date and end_date:
        # Validate date format
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
            date_range = quote(f"{start_date} {end_date}")
            print_func(f"Encoded date range: {date_range}")
        except ValueError:
            print_func("Error: Dates must be in YYYY-MM-DD format")
            return
    else:
        date_range = "all"
        print_func("Using default date range: all")
    
    # Construct the URL using format
    try:
        formatted_url = url_template.format(date_range=date_range, query=query, geo='us')
        print_func(f"\nTesting URL: {formatted_url}")
    except KeyError as e:
        print_func(f"Error formatting URL: {str(e)}")
        print_func(f"URL template: {url_template}")
        print_func(f"date_range: {date_range}")
        print_func(f"query: {query}")
        return
    except Exception as e:
        print_func(f"Unexpected error formatting URL: {str(e)}")
        return
    
    # Open URL in Safari
    print_func("Attempting to open URL in Safari...")
    open_url_in_safari(formatted_url, print_func)
    
    # Check for expected elements on the page
    confirm_terms = config['terms']
    print_func("\nChecking for expected elements...")
    if not confirm_page(confirm_terms=confirm_terms, print_func=print_func, max_tries=3, wait_time=2):
        print_func("Warning: Some expected elements were not found on the page")
    
    # Parse the page using the provided parser
    print_func("\nParsing page content...")
    if result_parser:
        html = result_parser(print_func)
        print_func(html)

def search_applescript_safari(
    search_term: Union[str, List[str]],
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    **kwargs
) -> Union[pd.DataFrame, Dict[str, Any]]:
    """
    Search Google Trends using Safari and AppleScript.
    
    Args:
        search_term (Union[str, List[str]]): The search term(s) to look up in Google Trends
        start_date (Optional[Union[str, datetime]]): Start date for the search
        end_date (Optional[Union[str, datetime]]): End date for the search
        **kwargs: Additional keyword arguments passed to API_Call
        
    Returns:
        Union[pd.DataFrame, Dict[str, Any]]: Standardized search results
    """
    safari = ApplescriptSafari(**locals())
    return safari.search(search_term, start_date, end_date).standardize_data().data

if __name__ == "__main__":
    # Define test configurations
    test_configs = [
        {
            "name": "Google Trends Test",
            "url": "https://trends.google.com/trends/explore?date={date_range}&geo=US&q={query}&hl=en",
            "search_terms": ["car", "truck"],
            "start_date": "2024-04-30",
            "end_date": "2024-05-30",
            "result_parser": parse_trends_page
        }
    ]
    
    # Create a new Safari window first
    # create_safari_window(print_func=print)
    # Check Google authentication
    if not get_google_auth(print_func=print):
        print("\nGoogle authentication check failed. Exiting...")
        sys.exit(1)

    # Run each test configuration
    for config in test_configs:
        print(f"\n{'='*50}")
        print(f"Running {config['name']}")
        print(f"{'='*50}")
        
        trends_applescript_safari(
            search_terms=config["search_terms"],
            start_date=config["start_date"],
            end_date=config["end_date"],
            result_parser=config["result_parser"]
        )

