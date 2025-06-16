import pytest
import io
import sys
from contextlib import redirect_stdout

def test_imports_prints_imported():
    """Test that imports.py prints 'imported' when imported"""
    # Capture stdout
    captured_output = io.StringIO()
    
    # Redirect stdout to our StringIO object
    with redirect_stdout(captured_output):
        # Import the module
        import gtrend_api_tools.APIs.imports
    
    # Get the output
    output = captured_output.getvalue().strip()
    
    # Check if "imported" is in the output
    assert "imported" in output, f"Expected 'imported' in output, got: {output}"

def test_test_function_returns_imported():
    """Test that test_function() returns 'imported'"""
    from gtrend_api_tools.APIs.imports import test_function
    result = test_function()
    assert result == "imported", f"Expected 'imported', got: {result}" 