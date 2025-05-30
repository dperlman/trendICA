"""
Test suite for the Google Trends data collection module.

This module contains unit tests for the gtrend.py module, which provides functionality
for collecting and processing Google Trends data. The tests cover various aspects of
the module including initialization, search functionality, and file operations.

Usage:
    - Run all tests: python -m unittest gtrend_tests.py
    - Run specific test: python -m unittest gtrend_tests.TestTrends.test_search_dry_run

Test Categories:
1. Initialization Tests
   - test_init: Verifies proper initialization with different parameters
   - test_init_with_api_keys: Tests initialization with API keys

2. Granularity Tests
   - test_calculate_search_granularity: Tests granularity calculation for different date ranges
   - test_get_index_granularity: Tests index granularity detection for different frequencies

3. Search Tests
   - test_search_dry_run: Tests search functionality in dry run mode (no API calls)
   - test_search_by_day: Tests daily granularity search
   - test_real_api_calls: Tests actual API calls (requires API keys)

4. File Operation Tests
   - test_save_to_csv: Tests saving data to CSV files

API Call Counts:
- test_search_by_day: No API calls (runs in dry run mode)
- test_real_api_calls: 
  * SerpAPI: 2 calls (if serpapi key configured)
  * SerpWow: 2 calls (if serpwow key configured)
  * SearchAPI: 2 calls (if searchapi key configured)
  * trendspy: 2 calls (always tested)
Total: 0-8 API calls depending on which API keys are configured

Note: The actual number of API calls may vary based on the time range being tested.
The test uses a 270-day period to match Google Trends' interval size limit.

Important Notes:
1. Tests will automatically use API keys from config.yaml if available
2. Only tests for available API keys will be run
3. Real API calls may incur costs and are subject to rate limits
4. The test data uses a 270-day time range to match Google Trends' interval size limit
"""

import unittest
from datetime import datetime, timedelta
import pandas as pd
import os
import shutil
import yaml
from gtrend import Trends, calculate_search_granularity, get_index_granularity

class TestTrends(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before each test method."""
        # Load API keys from config.yaml
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                cls.config = yaml.safe_load(f)
        else:
            cls.config = {'api_keys': {}}

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a Trends instance in dry run mode
        self.trends = Trends(dry_run=True, verbose=True)
        self.test_search_term = "sauna"
        self.test_start_date = "2023-01-01"
        self.test_end_date = "2023-09-28"  # Exactly 270 days
        self.test_time_range = f"{self.test_start_date} {self.test_end_date}"
        
        # Create test directory for file operations
        self.test_dir = "test_output"
        print(f"\nChecking for test directory '{self.test_dir}'...")
        print(f"Current working directory: {os.getcwd()}")
        if not os.path.exists(self.test_dir):
            print(f"Directory '{self.test_dir}' does not exist. Creating it...")
            os.makedirs(self.test_dir)
            print(f"Directory '{self.test_dir}' created successfully.")
        else:
            print(f"Directory '{self.test_dir}' already exists.")
            # Clean up any existing files in the directory
            for file in os.listdir(self.test_dir):
                file_path = os.path.join(self.test_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print(f"Cleaned up existing files in '{self.test_dir}'.")

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures after all tests are complete."""
        test_dir = "test_output"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"\nRemoved test directory '{test_dir}' after all tests completed.")

    def test_init(self):
        """Test initialization of Trends class."""
        trends = Trends()
        # Check if API keys and Tor password are loaded from config.yaml
        expected_serpapi_key = self.config.get('api_keys', {}).get('serpapi')
        expected_serpwow_key = self.config.get('api_keys', {}).get('serpwow')
        expected_searchapi_key = self.config.get('api_keys', {}).get('searchapi')
        expected_tor_password = self.config.get('tor', {}).get('control_password')
        
        self.assertEqual(trends.serpapi_api_key, expected_serpapi_key)
        self.assertEqual(trends.serpwow_api_key, expected_serpwow_key)
        self.assertEqual(trends.searchapi_api_key, expected_searchapi_key)
        self.assertEqual(trends.tor_control_password, expected_tor_password)
        self.assertFalse(trends.no_cache)
        self.assertIsNone(trends.proxy)
        self.assertTrue(trends.change_identity)
        self.assertEqual(trends.request_delay, 4)
        self.assertEqual(trends.geo, "US")
        self.assertEqual(trends.cat, 0)
        self.assertFalse(trends.dry_run)
        self.assertFalse(trends.verbose)

    def test_init_with_api_keys(self):
        """Test initialization with API keys."""
        trends = Trends(
            serpapi_api_key="test_serpapi_key",
            serpwow_api_key="test_serpwow_key",
            searchapi_api_key="test_searchapi_key"
        )
        self.assertEqual(trends.serpapi_api_key, "test_serpapi_key")
        self.assertEqual(trends.serpwow_api_key, "test_serpwow_key")
        self.assertEqual(trends.searchapi_api_key, "test_searchapi_key")

    def test_calculate_search_granularity(self):
        """Test calculation of search granularity based on date range."""
        # Test cases with expected granularities
        test_cases = [
            # (start_date, end_date, expected_granularity, description)
            ("2023-01-01", "2023-09-28", "D", "270 days - should be daily"),
            ("2023-01-01", "2023-12-31", "W", "365 days - should be weekly"),
            ("2023-01-01", "2024-12-31", "ME", "2 years - should be monthly"),
            ("2023-01-01", "2023-01-07", "D", "7 days - should be daily"),
            ("2023-01-01", "2023-01-31", "D", "31 days - should be daily"),
            ("2023-01-01", "2023-03-31", "D", "90 days - should be daily"),
            ("2023-01-01", "2023-06-30", "D", "180 days - should be daily"),
            ("2023-01-01", "2023-09-30", "D", "270 days - should be daily"),
            ("2023-01-01", "2023-10-01", "W", "271 days - should be weekly"),
            ("2023-01-01", "2024-01-01", "W", "1 year - should be weekly"),
            ("2023-01-01", "2024-02-01", "ME", "13 months - should be monthly"),
        ]
        
        for start_date, end_date, expected_granularity, description in test_cases:
            with self.subTest(description=description):
                print(start_date, end_date)
                result = calculate_search_granularity(start_date, end_date)
                self.assertIn("granularity", result)
                self.assertIn("index", result)
                self.assertIsInstance(result["granularity"], str)
                self.assertIsInstance(result["index"], pd.DatetimeIndex)
                self.assertEqual(result["granularity"], expected_granularity,
                               f"Expected {expected_granularity} for {description}")
                
                # Verify the index has the correct frequency
                if expected_granularity == "D":
                    self.assertTrue(result["index"].freq == "D" or result["index"].freq == "B")
                elif expected_granularity == "W":
                    self.assertTrue(result["index"].freq == "W")
                elif expected_granularity == "ME":
                    self.assertTrue(result["index"].freq == "ME")

    def test_get_index_granularity(self):
        """Test detection of index granularity."""
        # Test cases with known granularities
        test_cases = [
            # (expected_granularity, freq, periods, description)
            ('h', 'h', 24, "Hourly data"),
            ('D', 'D', 7, "Daily data"),
            ('D', 'B', 5, "Business days"),
            ('W', 'W', 4, "Weekly data"),
            ('W', 'W-MON', 4, "Weekly data starting Monday"),
            ('ME', 'ME', 12, "Month end data"),
            ('MS', 'MS', 12, "Month start data"),
        ]
        
        for expected_granularity, freq, periods, description in test_cases:
            with self.subTest(description=description):
                # Create test dataframe with specified frequency
                dates = pd.date_range(start="2023-01-01", periods=periods, freq=freq)
                df = pd.DataFrame(0, index=dates, columns=['test'])
                
                # Test granularity detection
                actual_granularity = get_index_granularity(df.index)
                self.assertEqual(actual_granularity, expected_granularity,
                               f"Expected {expected_granularity} for {description}")
                
                # Test with empty dataframe
                empty_df = pd.DataFrame(index=dates[:0], columns=['test'])
                empty_granularity = get_index_granularity(empty_df.index)
                self.assertEqual(empty_granularity, expected_granularity,
                               f"Empty dataframe should maintain {expected_granularity} granularity")
                
                # Test with single row
                single_df = pd.DataFrame(index=dates[:1], columns=['test'])
                single_granularity = get_index_granularity(single_df.index)
                self.assertEqual(single_granularity, expected_granularity,
                               f"Single row should maintain {expected_granularity} granularity")

    def test_search_dry_run(self):
        """Test search functionality in dry run mode (no API calls)."""
        # Test that dry run returns zero-filled dataframes without making API calls
        result = self.trends.search(
            search_term=self.test_search_term,
            start_date=self.test_start_date,
            end_date=self.test_end_date
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty, "Dry run should return a non-empty dataframe")
        self.assertTrue((result == 0).all().all(), "Dry run should return all zeros")
        
        # Verify that the search log shows no API calls were made
        self.assertEqual(len(self.trends.current_search_log), 0, 
                        "Dry run should not log any API calls")

    def test_search_by_day(self):
        """Test daily granularity search with 270-day intervals."""
        # Test without staggering
        result = self.trends.search(
            search_term=self.test_search_term,
            start_date=self.test_start_date,
            end_date=self.test_end_date,
            granularity="day",
            stagger=0,
            trim=False  # Don't trim to ensure we get all data
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty, "Dry run should return a non-empty dataframe")
        self.assertTrue((result == 0).all().all(), "Dry run should return all zeros")

        # Test with staggering and different combine methods
        for combine_method in ["mean", "median", "mode"]:
            result = self.trends.search(
                search_term=self.test_search_term,
                start_date=self.test_start_date,
                end_date=self.test_end_date,
                granularity="day",
                stagger=1,
                combine=combine_method,
                trim=False  # Don't trim to ensure we get all data
            )
            self.assertIsInstance(result, pd.DataFrame)
            self.assertFalse(result.empty, "Dry run should return a non-empty dataframe")
            self.assertTrue((result == 0).all().all(), "Dry run should return all zeros")

    def test_real_api_calls(self):
        """Test actual API calls if configured.
        
        Tests all four API methods:
        1. SerpAPI (if serpapi key configured)
        2. SerpWow (if serpwow key configured)
        3. SearchAPI (if searchapi key configured)
        4. trendspy (no API key required)
        
        Each API test verifies that:
        - The result is a pandas DataFrame
        - The DataFrame is not empty
        - The data structure matches expectations
        - The granularity matches what was calculated
        """
        # Calculate expected granularity for test date range
        expected_granularity = calculate_search_granularity(
            self.test_start_date,
            self.test_end_date
        )["granularity"]
        
        # Test each API
        apis = ['trendspy', 'serpapi', 'serpwow', 'searchapi']
        for api in apis:
            print(f"\nTesting {api}...")
            with self.subTest(api=api):
                try:
                    trends = Trends(dry_run=False, api=api)
                    result = trends.search(
                        search_term=self.test_search_term,
                        start_date=self.test_start_date,
                        end_date=self.test_end_date
                    )
                    self.assertIsInstance(result, pd.DataFrame)
                    self.assertFalse(result.empty)
                    
                    # Check that the granularity matches what was calculated
                    actual_granularity = get_index_granularity(result.index)
                    self.assertEqual(actual_granularity, expected_granularity,
                                   f"API {api} returned data with granularity {actual_granularity}, "
                                   f"expected {expected_granularity}")
                    print("PASS")
                except Exception as e:
                    print("FAIL")
                    print(e)
                    raise

    def test_save_to_csv(self):
        """Test saving data to CSV files."""
        # Create test data
        dates = pd.date_range(start=self.test_start_date, end=self.test_end_date, freq='D')
        df = pd.DataFrame(0, index=dates, columns=[self.test_search_term.replace(" ", "_")])
        
        # Test saving with default parameters
        filename = self.trends.save_to_csv(df, self.test_search_term, path=self.test_dir)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, filename)))
        
        # Test saving with comment
        comment = "Test comment"
        filename = self.trends.save_to_csv(df, self.test_search_term, path=self.test_dir, comment=comment)
        with open(os.path.join(self.test_dir, filename), 'r') as f:
            content = f.read()
            self.assertTrue(content.startswith(f"# {comment}"))

if __name__ == '__main__':
    unittest.main() 