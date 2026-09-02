"""Unit tests for date and timestamp transformation utilities."""

import sys
sys.path.insert(0, '/Workspace/Users/ayyub.orujzada@gmail.com/softserve-databricks-academy/week07/lab7_testing_dq/src')

from datetime import datetime
from transformations.date_utils import parse_unix_timestamp


class TestParseUnixTimestamp:
    """Tests for parse_unix_timestamp function."""
    
    def test_valid_timestamp_2019(self):
        """Test parsing of valid Unix timestamp from 2019 (Lab 5/6 data range)."""
        # 2019-07-15 12:00:00 UTC
        result = parse_unix_timestamp(1563192000)
        assert result is not None
        assert result.year == 2019
        assert result.month == 7
        assert result.day == 15
    
    def test_valid_timestamp_epoch(self):
        """Test parsing of epoch start (1970-01-01)."""
        result = parse_unix_timestamp(1)
        assert result is not None
        assert result.year == 1970
        assert result.month == 1
        assert result.day == 1
    
    def test_valid_timestamp_recent(self):
        """Test parsing of recent timestamp (2020s)."""
        # 2020-01-01 00:00:00 UTC
        result = parse_unix_timestamp(1577836800)
        assert result is not None
        assert result.year == 2020
        assert result.month == 1
    
    def test_none_input(self):
        """Test handling of None input."""
        assert parse_unix_timestamp(None) is None

    def test_non_numeric_input(self):
        """Test malformed source values are rejected without raising."""
        assert parse_unix_timestamp("not-a-timestamp") is None
    
    def test_negative_timestamp(self):
        """Test handling of negative timestamp (before epoch)."""
        assert parse_unix_timestamp(-1) is None
    
    def test_zero_timestamp(self):
        """Test handling of zero timestamp."""
        assert parse_unix_timestamp(0) is None
    
    def test_very_large_timestamp(self):
        """Test handling of excessively large timestamp (overflow protection)."""
        # Year 3000+ timestamp should be handled gracefully
        result = parse_unix_timestamp(999999999999)
        # Either returns None or a valid far-future date
        if result is not None:
            assert isinstance(result, datetime)