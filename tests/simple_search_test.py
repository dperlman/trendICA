import os
import sys

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from gtrend_api_tools import Trends
from gtrend_api_tools import load_config
from datetime import datetime
import json

def test_search(trends_instance, test_case):
    """Test a search with the specified parameters and save results to files."""
    print(f"\n{'='*50}")
    print(f"Testing search with parameters:")
    print(f"  Search term: {test_case['search_term']}")
    print(f"  Start date: {test_case['start_date']}")
    print(f"  End date: {test_case.get('end_date', 'None')}")
    print(f"  Granularity: {test_case.get('granularity', 'None (default)')}")
    print(f"{'='*50}")
    
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        # Perform the search
        search_params = {
            'search_term': test_case['search_term'],
            'start_date': test_case['start_date'],
            'end_date': test_case.get('end_date')
        }
        
        # Only add granularity if it's specified
        if 'granularity' in test_case:
            search_params['granularity'] = test_case['granularity']
            
        # Chain the method calls
        trends_instance.search(**search_params).standardize_data()
        
        # Create test_outputs directory if it doesn't exist
        os.makedirs('test_outputs', exist_ok=True)
        
        # Get the data from the trends instance
        results = trends_instance.data
        
        # Convert results to formatted JSON string
        results_str = json.dumps(results, indent=2, sort_keys=True)
        
        # Save results to text file
        output_file = os.path.join('test_outputs', 
            f"search_{test_case['search_term'].replace(' ', '_')}_{current_time}.txt")
        with open(output_file, 'w') as f:
            f.write(results_str)
        print(f"Results saved to {output_file}")
            
    except Exception as e:
        print(f"Error during search: {str(e)}")
        raise

def main():
    # Load configuration
    config = load_config()
    
    # Get verbose flag from config or default to True
    verbose = config.get('verbose', 'INFO')
    
    # Initialize Trends instance with smart_tpy mode
    trends = Trends(
        use_api="applescript_safari",
        verbose=verbose,
        proxy="127.0.0.1:9150",
        change_identity=True
    )
    
    # Define test cases
    test_cases = [
        {
            'search_term': 'coffee,tea',
            'start_date': '2024-01-01',
            'end_date': '2024-03-01',
            'granularity': 'D'  # Daily granularity using pandas frequency string
        },
        {
            'search_term': 'coffee,tea',
            'start_date': '2023-01-01',
            'end_date': '2023-03-01'
            # No granularity specified to test default behavior
        }
        # {
        #     'search_term': 'bitcoin,ethereum,cardano,dogecoin,solana',
        #     'start_date': '2024-01-01',
        #     'end_date': '2024-02-01',
        #     'granularity': 'D'
        # }
    ]
    
    # Run each test case
    for test_case in test_cases:
        test_search(trends, test_case)

if __name__ == "__main__":
    main() 