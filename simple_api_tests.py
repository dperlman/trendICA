from APIs import SerpApi, SerpWow, TrendsPy, SearchApi, SerpApiPy
from datetime import datetime
from utils import load_config, _print_if_verbose
import json
import os

def test_api(api_instance, api_name, verbose: bool = False):
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
            start_date="2024-01-01",
            end_date="2024-09-27"  # 270 days from start
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
        print(f"Standardized results saved to {standardized_output_file}")
            
    except Exception as e:
        print(f"Error testing {api_name}: {str(e)}")

def main():
    # Load configuration
    config = load_config()
    
    # Get verbose flag from config or default to True
    verbose = config.get('verbose', True)
    
    tor_control_password = config.get('tor', {}).get('control_password')
    
    # Initialize API instances with their respective keys
    # apis = {
    #     "SerpApi": SerpApi(api_key=config.get('api_keys', {}).get('serpapi'), verbose=verbose),
    #     "SerpWow": SerpWow(api_key=config.get('api_keys', {}).get('serpwow'), verbose=verbose),
    #     "TrendsPy": TrendsPy(verbose=verbose, tor_control_password=tor_control_password, proxy="127.0.0.1:9150", change_identity=True),
    #     "SearchApi": SearchApi(api_key=config.get('api_keys', {}).get('searchapi'), verbose=verbose)
    # }
    apis = {
        "SerpApi": SerpApi(api_key=config.get('api_keys', {}).get('serpapi'), verbose=verbose),
        "SerpWow": SerpWow(api_key=config.get('api_keys', {}).get('serpwow'), verbose=verbose),
        "SearchApi": SearchApi(api_key=config.get('api_keys', {}).get('searchapi'), verbose=verbose)
    }
    # apis = {
    #     "SerpApiPy": SerpApiPy(api_key=config.get('api_keys', {}).get('serpapi'), verbose=verbose)
    # }
    # apis = {
    #     "SerpApi": SerpApi(api_key=config.get('api_keys', {}).get('serpapi'), verbose=verbose)
    # }
    # apis = {
    #     "SerpWow": SerpWow(api_key=config.get('api_keys', {}).get('serpwow'), verbose=verbose)
    # }    
    # apis = {
    #     "SearchApi": SearchApi(api_key=config.get('api_keys', {}).get('searchapi'), verbose=verbose)
    # }
    # apis = {
    #     "TrendsPy": TrendsPy(verbose=verbose, tor_control_password=tor_control_password, proxy="127.0.0.1:9150", change_identity=True)
    # }
    # Test each API
    for api_name, api_instance in apis.items():
        test_api(api_instance, api_name, verbose)

if __name__ == "__main__":
    main() 