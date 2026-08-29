"""Unit tests for string transformation utilities."""

import sys
sys.path.insert(0, '/Workspace/Users/ayyub.orujzada@gmail.com/softserve-databricks-academy/week07/lab7_testing_dq/src')

from transformations.string_utils import normalize_customer_name


class TestNormalizeCustomerName:
    """Tests for normalize_customer_name function."""
    
    def test_standard_name(self):
        """Test normalization of standard mixed-case name."""
        assert normalize_customer_name("john doe") == "John Doe"
    
    def test_uppercase_name(self):
        """Test normalization of all uppercase name."""
        assert normalize_customer_name("ALICE SMITH") == "Alice Smith"
    
    def test_lowercase_name(self):
        """Test normalization of all lowercase name."""
        assert normalize_customer_name("bob johnson") == "Bob Johnson"
    
    def test_name_with_leading_whitespace(self):
        """Test trimming of leading whitespace."""
        assert normalize_customer_name("  Jane Doe") == "Jane Doe"
    
    def test_name_with_trailing_whitespace(self):
        """Test trimming of trailing whitespace."""
        assert normalize_customer_name("Jane Doe  ") == "Jane Doe"
    
    def test_name_with_surrounding_whitespace(self):
        """Test trimming of surrounding whitespace and case normalization."""
        assert normalize_customer_name("  john DOE  ") == "John Doe"
    
    def test_name_with_multiple_spaces(self):
        """Test name with multiple internal spaces."""
        assert normalize_customer_name("mary  ann  jones") == "Mary  Ann  Jones"
    
    def test_single_name(self):
        """Test single name (no surname)."""
        assert normalize_customer_name("madonna") == "Madonna"
    
    def test_none_input(self):
        """Test handling of None input."""
        assert normalize_customer_name(None) is None
    
    def test_empty_string(self):
        """Test handling of empty string."""
        assert normalize_customer_name("") == ""
    
    def test_whitespace_only(self):
        """Test handling of whitespace-only string."""
        assert normalize_customer_name("   ") == ""