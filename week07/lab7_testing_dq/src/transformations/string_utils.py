"""String transformation utilities for Lab 7 testing.

Based on Lab 5 Silver pipeline string normalization logic.
"""


def normalize_customer_name(raw_name: str) -> str:
    """Standardizes customer name: trim whitespace and convert to Title Case.
    
    Replicates PySpark logic:
        F.initcap(F.trim(F.col("customer_name")))
    
    Args:
        raw_name: Raw customer name string from source data
        
    Returns:
        Normalized name in Title Case with whitespace trimmed,
        or None if input is None
        
    Examples:
        >>> normalize_customer_name("  john DOE  ")
        'John Doe'
        >>> normalize_customer_name("ALICE SMITH")
        'Alice Smith'
        >>> normalize_customer_name(None)
        None
    """
    if raw_name is None:
        return None
    return raw_name.strip().title()