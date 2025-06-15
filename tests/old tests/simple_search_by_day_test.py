from gtrend import Trends
from datetime import datetime
from utils import load_config
import os
import json

def test_search(trends_instance, test_case):
    """Test a search with the specified parameters and save results to files."""
    print(f"\n{'='*50}")
    print(f"Testing search_by_day with parameters:")
    print(f"  Search term: {test_case['search_term']}")
    print(f"  Start date: {test_case['start_date']}")
    print(f"  End date: {test_case.get('end_date', 'None')}")
    print(f"{'='*50}")
    
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        # Perform the search using search_by_day
        results = trends_instance.search_by_day(
            search_term=test_case['search_term'],
            start_date=test_case['start_date'],
            end_date=test_case.get('end_date')
        )
        
        # Create test_outputs directory if it doesn't exist
        os.makedirs('test_outputs', exist_ok=True)
        
        # Convert results to formatted JSON string
        results_str = json.dumps(results, indent=2, sort_keys=True)
        
        # Save results to text file
        output_file = os.path.join('test_outputs', 
            f"search_by_day_{test_case['search_term'].replace(' ', '_')}_{current_time}.txt")
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
    verbose = config.get('verbose', True)
    
    # Initialize Trends instance with smart_tpy mode
    trends = Trends(
        api="smart_tpy",
        verbose=verbose,
        proxy="127.0.0.1:9150",
        change_identity=True
    )
    
    # Define test cases
    test_cases = [
        {
            'search_term': 'coffee,tea',
            'start_date': '2024-01-01',
            'end_date': '2024-03-01'
        },
        {
            'search_term': 'bitcoin,ethereum,cardano,dogecoin,solana',
            'start_date': '2024-01-01',
            'end_date': '2024-02-01'
        }
    ]
    
    # Run each test case
    for test_case in test_cases:
        test_search(trends, test_case)

if __name__ == "__main__":
    main() 