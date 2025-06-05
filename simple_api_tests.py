from APIs import SerpApi, SerpWow, TrendsPy, SearchApi, SerpApiPy, ApplescriptSafari, DummyApi
from datetime import datetime
from utils import load_config, _print_if_verbose
import json
import os
import traceback

def test_api(api_instance, api_name, start_date, end_date, verbose: bool = False):
    """Test an API instance with the specified parameters and save results to files."""
    print(f"\n{'='*50}")
    print(f"Testing {api_name}")
    print(f"{'='*50}")
    
    search_term = "coffee,tea"
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        # Get both raw and standardized data
        api_instance.search(
            search_term=search_term,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None
        )
        raw_data = api_instance.raw_data
        standardized_data = api_instance.standardize_data().data

        # Create test_outputs directory if it doesn't exist
        os.makedirs('test_outputs', exist_ok=True)
        
        # Convert results to formatted JSON strings
        raw_data_str = json.dumps(raw_data, indent=2, sort_keys=True)
        standardized_data_str = json.dumps(standardized_data, indent=2, sort_keys=True)

        # Save raw data to file
        raw_output_file = os.path.join('test_outputs', f"{api_name}_{search_term.replace(' ', '_')}_{current_time}_raw.txt")
        with open(raw_output_file, 'w') as f:
            f.write(raw_data_str)
        print(f"Raw results saved to {raw_output_file}")
        
        # Save standardized data to file
        standardized_output_file = os.path.join('test_outputs', f"{api_name}_{search_term.replace(' ', '_')}_{current_time}_standardized.txt")
        with open(standardized_output_file, 'w') as f:
            f.write(standardized_data_str)
        print(f"Standardized results ({len(standardized_data)} records) saved to {standardized_output_file}")
            
    except Exception as e:
        print(f"Error testing {api_name}: {str(e)}")
        print(traceback.format_exc())

def main():
    # Load configuration
    config = load_config()
    
    # Get verbose flag from config or default to True
    verbose = config.get('verbose', False)
    
    tor_control_password = config.get('tor', {}).get('control_password')

    start_date = "2024-01-01"
    #end_date = "2024-09-26"
    end_date = "2029-03-14" # 1899 days
    #end_date = "2029-03-15" # 1900 days
    #end_date = "2029-03-16" # 1901 days
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    days_diff = (end_dt - start_dt).days
    print(f"\n{'='*50}")
    print(f"Start date: {start_date}, End date: {end_date}, Days difference: {days_diff}")
    print(f"{'='*50}")

    
    # Initialize API instances with their respective keys

    apis = {
        #"SerpApi": SerpApi(api_key=config.get('api_keys', {}).get('serpapi'), verbose=verbose),
        #"SerpWow": SerpWow(api_key=config.get('api_keys', {}).get('serpwow'), verbose=verbose),
        #"SearchApi": SearchApi(api_key=config.get('api_keys', {}).get('searchapi'), verbose=verbose),
        #"ApplescriptSafari": ApplescriptSafari(verbose=verbose),
        #"TrendsPy": TrendsPy(verbose=verbose, tor_control_password=tor_control_password, proxy="127.0.0.1:9150", change_identity=True),
        "DummyApi": DummyApi(verbose=verbose)
    }

    # Test each API
    for api_name, api_instance in apis.items():
        test_api(api_instance, api_name, start_date, end_date, verbose)

if __name__ == "__main__":
    main() 