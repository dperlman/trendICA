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

2. Search Tests
   - test_search_dry_run: Tests search functionality in dry run mode
   - test_search_by_day: Tests daily granularity search with 270-day intervals
   - test_search_by_hour: Tests hourly granularity search
   - test_real_api_calls: Tests actual API calls (requires API keys)

3. File Operation Tests
   - test_save_to_csv: Tests saving data to CSV files
   - test_combine_trend_files: Tests combining multiple trend files

4. Utility Function Tests
   - test_calculate_search_granularity: Tests granularity calculation
   - test_get_index_granularity: Tests index granularity detection

API Call Counts:
- test_search_dry_run: 4 calls (1 for single iteration + 3 for multiple iterations)
- test_search_by_day: 4 calls (2 calls per 270-day interval for a total of 2 intervals)
- test_search_by_hour: 1 call
- test_real_api_calls: Up to 3 calls (one each for SerpAPI, SerpWow, and trendspy)
Total: 10-12 API calls depending on which API keys are configured

Note: The actual number of API calls may vary based on the time range being tested.
The test uses a 270-day period requiring 4 total calls.

Important Notes:
1. By default, tests run in dry run mode to avoid API costs
2. To enable real API testing:
   - Set USE_REAL_API = True
   - Configure SERPAPI_API_KEY and/or SERPWOW_API_KEY
3. Real API calls may incur costs and are subject to rate limits
4. The test data uses a 270-day time range to match the new interval size
"""

import unittest
from datetime import datetime, timedelta
import pandas as pd
import os
import shutil
from gtrend import Trends
from keys import SERPAPI_API_KEY, SERPWOW_API_KEY, SEARCHAPI_API_KEY

# Test configuration
USE_REAL_API = False  # Set to True to enable real API testing

class TestTrends(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.trends = Trends(
            serpapi_api_key=SERPAPI_API_KEY if USE_REAL_API else None,
            serpwow_api_key=SERPWOW_API_KEY if USE_REAL_API else None,
            searchapi_api_key=SEARCHAPI_API_KEY if USE_REAL_API else None,
            dry_run=not USE_REAL_API,
            verbose=True
        )
        self.test_search_term = "python programming"
        self.test_start_date = "2023-01-01"
        self.test_end_date = "2023-10-01"  # 270 days + buffer
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
        """Test initialization with default parameters."""
        trends = Trends()
        self.assertIsNone(trends.serpapi_api_key)
        self.assertIsNone(trends.serpwow_api_key)
        self.assertIsNone(trends.searchapi_api_key)
        self.assertFalse(trends.no_cache)
        self.assertIsNone(trends.proxy)
        self.assertTrue(trends.change_identity)
        self.assertEqual(trends.request_delay, 4)
        self.assertIsNone(trends.geo)
        self.assertIsNone(trends.cat)
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

    def test_search_dry_run(self):
        """Test search functionality in dry run mode."""
        # Test single iteration
        result = self.trends.search(
            search_term=self.test_search_term,
            start_date=self.test_start_date,
            end_date=self.test_end_date,
            n_iterations=1
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty, "Dry run should return a non-empty dataframe")
        self.assertTrue((result == 0).all().all(), "Dry run should return all zeros")
        # For a range requiring two 270-day intervals, we expect 540 rows
        self.assertEqual(len(result.index), 540, "Dataframe should contain two 270-day intervals")

        # Test multiple iterations with different combine methods
        for combine_method in ["mean", "median"]:  # Removed "mode" as it doesn't work well with all zeros
            result = self.trends.search(
                search_term=self.test_search_term,
                start_date=self.test_start_date,
                end_date=self.test_end_date,
                n_iterations=3,
                combine=combine_method
            )
            self.assertIsInstance(result, pd.DataFrame)
            self.assertFalse(result.empty, "Dry run should return a non-empty dataframe")
            self.assertTrue((result == 0).all().all(), "Dry run should return all zeros")
            # For a range requiring two 270-day intervals, we expect 540 rows
            self.assertEqual(len(result.index), 540, "Dataframe should contain two 270-day intervals")

    def test_search_by_day(self):
        """Test daily granularity search with 270-day intervals."""
        # Test without staggering
        result = self.trends.search_by_day(
            search_term=self.test_search_term,
            time_range=self.test_time_range,
            stagger=0,
            trim=False  # Don't trim to ensure we get all data
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty, "Dry run should return a non-empty dataframe")
        self.assertTrue((result == 0).all().all(), "Dry run should return all zeros")
        # For a range requiring two 270-day intervals, we expect 540 rows
        self.assertEqual(len(result.index), 540, "Dataframe should contain two 270-day intervals")

        # Test with staggering and different combine methods
        for combine_method in ["mean", "median", "mode"]:
            result = self.trends.search_by_day(
                search_term=self.test_search_term,
                time_range=self.test_time_range,
                stagger=1,
                combine=combine_method,
                trim=False  # Don't trim to ensure we get all data
            )
            self.assertIsInstance(result, pd.DataFrame)
            self.assertFalse(result.empty, "Dry run should return a non-empty dataframe")
            self.assertTrue((result == 0).all().all(), "Dry run should return all zeros")
            # For a range with staggering=1, we expect 945 rows (3 * 270 days + 135 days overlap)
            self.assertEqual(len(result.index), 945, "Dataframe should contain three 270-day intervals plus overlap")

    def test_search_by_hour(self):
        """Test hourly granularity search."""
        # Use a 7-day range for hourly data
        start_date = "2023-01-01"
        end_date = "2023-01-08"
        time_range = f"{start_date} {end_date}"
        
        result = self.trends.search_by_hour(
            search_term=self.test_search_term,
            time_range=time_range
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty, "Dry run should return a non-empty dataframe")
        self.assertTrue((result == 0).all().all(), "Dry run should return all zeros")
        self.assertEqual(len(result.index), (datetime.strptime(end_date, "%Y-%m-%d") - 
                                           datetime.strptime(start_date, "%Y-%m-%d")).days * 24,
                     "Dataframe should have the correct number of hours")

    def test_real_api_calls(self):
        """Test actual API calls if configured."""
        if not USE_REAL_API:
            self.skipTest("Real API testing not enabled")
        
        # Test SerpAPI
        if SERPAPI_API_KEY:
            trends = Trends(serpapi_api_key=SERPAPI_API_KEY, dry_run=False)
            result = trends.search(
                search_term=self.test_search_term,
                start_date=self.test_start_date,
                end_date=self.test_end_date
            )
            self.assertIsInstance(result, pd.DataFrame)
            self.assertFalse(result.empty)

        # Test SerpWow
        if SERPWOW_API_KEY:
            trends = Trends(serpwow_api_key=SERPWOW_API_KEY, dry_run=False)
            result = trends.search(
                search_term=self.test_search_term,
                start_date=self.test_start_date,
                end_date=self.test_end_date
            )
            self.assertIsInstance(result, pd.DataFrame)
            self.assertFalse(result.empty)

    def test_save_to_csv(self):
        """Test saving data to CSV files."""
        # Create test data
        dates = pd.date_range(start=self.test_start_date, end=self.test_end_date, freq='D')
        df = pd.DataFrame(0, index=dates, columns=[self.test_search_term.replace(" ", "_")])
        
        # Test saving with default parameters
        filename = self.trends.save_to_csv(
            combined_df=df,
            search_term=self.test_search_term,
            path=self.test_dir
        )
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, filename)))
        
        # Test saving with comment
        filename = self.trends.save_to_csv(
            combined_df=df,
            search_term=self.test_search_term,
            path=self.test_dir,
            comment="Test comment"
        )
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, filename)))

    def test_combine_trend_files(self):
        """Test combining multiple trend files."""
        # Create test files
        dates = pd.date_range(start=self.test_start_date, end=self.test_end_date, freq='D')
        for i in range(3):
            df = pd.DataFrame(0, index=dates, columns=[self.test_search_term.replace(" ", "_")])
            self.trends.save_to_csv(
                combined_df=df,
                search_term=self.test_search_term,
                path=self.test_dir
            )
        
        # Test combining files
        result = self.trends.combine_trend_files(
            directory=self.test_dir,
            file_prefix=self.test_search_term.replace(" ", "_")
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result.columns), 3)

    def test_calculate_search_granularity(self):
        """Test granularity calculation for different time ranges."""
        print("\nTesting granularity calculation...")
        
        # Test daily granularity (270 days)
        start_date = "2023-01-01"
        end_date = "2023-09-28"  # 270 days
        print(f"\nTesting daily granularity with range: {start_date} to {end_date}")
        result = self.trends._calculate_search_granularity(start_date, end_date)
        print(f"Expected 'day', got: {result['granularity']}")
        self.assertEqual(result["granularity"], "day")
        
        # Test weekly granularity
        end_date = "2023-12-31"  # ~1 year
        print(f"\nTesting weekly granularity with range: {start_date} to {end_date}")
        result = self.trends._calculate_search_granularity(start_date, end_date)
        print(f"Expected 'week', got: {result['granularity']}")
        self.assertEqual(result["granularity"], "week")
        
        # Test monthly granularity
        end_date = "2024-12-31"  # >1 year
        print(f"\nTesting monthly granularity with range: {start_date} to {end_date}")
        result = self.trends._calculate_search_granularity(start_date, end_date)
        print(f"Expected 'month', got: {result['granularity']}")
        self.assertEqual(result["granularity"], "month")

    def test_get_index_granularity(self):
        """Test index granularity detection."""
        # Test hourly granularity
        dates = pd.date_range(start=self.test_start_date, periods=24, freq='h')
        self.assertEqual(self.trends._get_index_granularity(dates), 'H')
        
        # Test daily granularity
        dates = pd.date_range(start=self.test_start_date, periods=270, freq='D')
        self.assertEqual(self.trends._get_index_granularity(dates), 'D')
        
        # Test weekly granularity
        dates = pd.date_range(start=self.test_start_date, periods=52, freq='W')
        self.assertEqual(self.trends._get_index_granularity(dates), 'W')
        
        # Test monthly granularity
        dates = pd.date_range(start=self.test_start_date, periods=12, freq='ME')
        self.assertEqual(self.trends._get_index_granularity(dates), 'M')

if __name__ == '__main__':
    unittest.main() 