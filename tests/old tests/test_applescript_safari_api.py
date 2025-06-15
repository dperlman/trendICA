from APIs.applescript_safari import ApplescriptSafari
from datetime import datetime

def main():
    # Create an instance with verbose output
    safari = ApplescriptSafari(verbose=True)
    
    # Define test parameters
    search_terms = ["python", "javascript"]
    start_date = "2024-01-01"
    end_date = "2024-03-01"
    
    print("\nStarting test...")
    print(f"Search terms: {search_terms}")
    print(f"Date range: {start_date} to {end_date}")
    
    # Perform the search
    safari.search(search_terms, start_date, end_date)
    
    # Get raw data
    print("\nRaw data (first 500 chars):")
    print(safari.raw_data[:500])
    
    # Standardize the data
    safari.standardize_data()
    
    # Get standardized data
    print("\nStandardized data (first three entries):")
    if safari.data:
        print(safari.data[:3])
    
    # Create DataFrame
    safari.make_dataframe()
    
    # Get DataFrame
    print("\nDataFrame head:")
    print(safari.dataframe.head())
    


if __name__ == "__main__":
    main() 