"""Business logic transformations for Lab 7 testing.

Based on Lab 6 Gold layer business rules.
"""

from decimal import Decimal
from typing import Optional, Tuple


def map_loyalty_segment(segment: Optional[int]) -> str:
    """Maps loyalty segment code to descriptive name.
    
    Replicates SQL logic from dim_customers:
        CASE c.loyalty_segment
            WHEN 0 THEN 'None'
            WHEN 1 THEN 'Bronze'
            WHEN 2 THEN 'Silver'
            WHEN 3 THEN 'Gold'
            ELSE 'Unknown'
        END
    
    Args:
        segment: Loyalty segment code (0-3)
        
    Returns:
        Segment name string ('None', 'Bronze', 'Silver', 'Gold', 'Unknown')
        
    Examples:
        >>> map_loyalty_segment(0)
        'None'
        >>> map_loyalty_segment(3)
        'Gold'
        >>> map_loyalty_segment(99)
        'Unknown'
    """
    mapping = {
        0: "None",
        1: "Bronze",
        2: "Silver",
        3: "Gold"
    }
    return mapping.get(segment, "Unknown")


def calculate_line_total_with_discount(
    price_cents: int,
    quantity: int,
    promo_disc_pct: Optional[float] = None
) -> Tuple[Decimal, Decimal]:
    """Calculates line total and promotion discount from cents to dollars.
    
    Replicates SQL logic from fct_sales_orders:
        CAST((price_cents * quantity) / 100.0 AS DECIMAL(10,2)) as line_total,
        CAST(COALESCE(price_cents * quantity * promo_disc_pct, 0) / 100.0 AS DECIMAL(10,2))
    
    Args:
        price_cents: Unit price in cents (e.g., 1500 = $15.00)
        quantity: Number of units ordered
        promo_disc_pct: Promotion discount percentage (e.g., 0.10 = 10% off)
        
    Returns:
        Tuple of (line_total, discount_amount) both as Decimal rounded to 2 places
        
    Raises:
        ValueError: If price_cents or quantity is None
        
    Examples:
        >>> calculate_line_total_with_discount(1500, 2, None)
        (Decimal('30.00'), Decimal('0.00'))
        >>> calculate_line_total_with_discount(1500, 2, 0.10)
        (Decimal('30.00'), Decimal('3.00'))
    """
    if price_cents is None or quantity is None:
        raise ValueError("price_cents and quantity are required")
    
    if price_cents < 0 or quantity < 0:
        raise ValueError("price_cents and quantity must be non-negative")
    
    line_total_cents = price_cents * quantity
    line_total = Decimal(line_total_cents) / Decimal(100)
    
    if promo_disc_pct and promo_disc_pct > 0:
        discount_cents = line_total_cents * Decimal(str(promo_disc_pct))
        discount = discount_cents / Decimal(100)
    else:
        discount = Decimal(0)
    
    return (
        round(line_total, 2),
        round(discount, 2)
    )