"""Date and timestamp transformation utilities for Lab 7 testing.

Based on Lab 5 Silver pipeline timestamp parsing logic.
"""

from datetime import datetime
from typing import Optional


def parse_unix_timestamp(unix_ts: Optional[int]) -> Optional[datetime]:
    """Converts Unix timestamp (seconds since epoch) to datetime.
    
    Replicates PySpark logic:
        F.to_timestamp(F.from_unixtime(F.col("valid_from").cast("bigint")))
    
    Args:
        unix_ts: Unix timestamp as integer (seconds since 1970-01-01)
        
    Returns:
        datetime object, or None if input is None or invalid
        
    Examples:
        >>> parse_unix_timestamp(1563192000)
        datetime.datetime(2019, 7, 15, 12, 0)
        >>> parse_unix_timestamp(None)
        None
        >>> parse_unix_timestamp(-1)
        None
    """
    if unix_ts is None or unix_ts <= 0:
        return None
    try:
        return datetime.fromtimestamp(unix_ts)
    except (ValueError, OSError, OverflowError):
        return None