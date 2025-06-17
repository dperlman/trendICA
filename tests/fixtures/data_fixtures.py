"""
Data-related test fixtures for gtrend_api_tools.
"""
import pytest
from datetime import datetime

@pytest.fixture(scope="module")
def test_terms():
    """Provide common test search terms."""
    return {
        'term1': "hamburger",
        'term2': "pizza",
        'term3': "hot dog",
        'term4': "ice cream",
        'term5': "coffee",
        'term6': "tea",
        'term7': "wine",
        'term8': "beer",
        'term9': "soda",
        'term10': "water"
    }

@pytest.fixture(scope="module")
def test_dates():
    """Provide common test date ranges."""
    return {
        'short_range': {
            'start': "2024-01-01",
            'end': "2024-01-07"
        },
        'medium_range': {
            'start': "2024-01-01",
            'end': "2024-01-10"
        },
        'datetime_range': {
            'start': datetime(2024, 1, 1),
            'end': datetime(2024, 1, 3)
        }
    } 