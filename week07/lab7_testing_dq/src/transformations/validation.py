"""Data validation utilities for Lab 7 testing.

Based on Lab 5/6 data quality expectations.
"""

from typing import Optional


def validate_loyalty_segment(segment: Optional[int]) -> bool:
    """Validates that loyalty segment is in the valid range [0-3].
    
    Based on business logic from:
    - silver_pipeline.py: F.col("loyalty_segment").cast("int")
    - dim_customers CASE: segments 0='None', 1='Bronze', 2='Silver', 3='Gold'
    
    Args:
        segment: Loyalty segment code to validate
        
    Returns:
        True if segment is valid (0, 1, 2, or 3), False otherwise
        
    Examples:
        >>> validate_loyalty_segment(0)
        True
        >>> validate_loyalty_segment(3)
        True
        >>> validate_loyalty_segment(99)
        False
        >>> validate_loyalty_segment(None)
        False
    """
    if segment is None:
        return False
    return 0 <= segment <= 3