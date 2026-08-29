"""Unit tests for data validation utilities."""

import sys
sys.path.insert(0, '/Workspace/Users/ayyub.orujzada@gmail.com/softserve-databricks-academy/week07/lab7_testing_dq/src')

from transformations.validation import validate_loyalty_segment


class TestValidateLoyaltySegment:
    """Tests for validate_loyalty_segment function."""
    
    def test_valid_segment_none(self):
        """Test validation of segment 0 (None tier)."""
        assert validate_loyalty_segment(0) is True
    
    def test_valid_segment_bronze(self):
        """Test validation of segment 1 (Bronze)."""
        assert validate_loyalty_segment(1) is True
    
    def test_valid_segment_silver(self):
        """Test validation of segment 2 (Silver)."""
        assert validate_loyalty_segment(2) is True
    
    def test_valid_segment_gold(self):
        """Test validation of segment 3 (Gold)."""
        assert validate_loyalty_segment(3) is True
    
    def test_invalid_segment_negative(self):
        """Test validation rejects negative segment."""
        assert validate_loyalty_segment(-1) is False
    
    def test_invalid_segment_too_large(self):
        """Test validation rejects segment above valid range."""
        assert validate_loyalty_segment(4) is False
        assert validate_loyalty_segment(99) is False
    
    def test_invalid_segment_none(self):
        """Test validation rejects None input."""
        assert validate_loyalty_segment(None) is False
    
    def test_boundary_lower(self):
        """Test validation at lower boundary (0)."""
        assert validate_loyalty_segment(0) is True
        assert validate_loyalty_segment(-1) is False
    
    def test_boundary_upper(self):
        """Test validation at upper boundary (3)."""
        assert validate_loyalty_segment(3) is True
        assert validate_loyalty_segment(4) is False