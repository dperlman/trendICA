import applescript
import time

def open_url_in_safari(url: str):
    script = f'''
    tell application "Safari"
        try
            tell window 1 to set current tab to make new tab with properties {{URL:"{url}"}}
        on error
            open location "{url}"
        end try
    end tell
    '''
    return applescript.run(script)

def run_applescript_test():
    # Test opening a URL in Safari
    url = "https://accounts.google.com/AccountChooser"
    result = open_url_in_safari(url)
    print(f"Result: {result.code}, {result.out}, {result.err}")
    time.sleep(10)
    url = "https://trends.google.com/trends/explore?date=2024-04-30%202024-05-30&geo=US&q=hamburger,hot%20dog&hl=en"
    result = open_url_in_safari(url)
    print(f"Result: {result.code}, {result.out}, {result.err}")

if __name__ == "__main__":
    run_applescript_test() 