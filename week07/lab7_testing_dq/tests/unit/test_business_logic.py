"""Unit tests for business logic transformations."""

from decimal import Decimal

import pytest

from transformations.business_logic import (
    calculate_line_total_with_discount,
    map_loyalty_segment,
)


class TestMapLoyaltySegment:
    """Tests for map_loyalty_segment function."""
    
    def test_segment_none(self):
        """Test mapping of segment 0 (None)."""
        assert map_loyalty_segment(0) == "None"
    
    def test_segment_bronze(self):
        """Test mapping of segment 1 (Bronze)."""
        assert map_loyalty_segment(1) == "Bronze"
    
    def test_segment_silver(self):
        """Test mapping of segment 2 (Silver)."""
        assert map_loyalty_segment(2) == "Silver"
    
    def test_segment_gold(self):
        """Test mapping of segment 3 (Gold)."""
        assert map_loyalty_segment(3) == "Gold"
    
    def test_segment_invalid_positive(self):
        """Test mapping of invalid positive segment."""
        assert map_loyalty_segment(99) == "Unknown"
    
    def test_segment_invalid_negative(self):
        """Test mapping of invalid negative segment."""
        assert map_loyalty_segment(-1) == "Unknown"
    
    def test_segment_none_input(self):
        """Test handling of None input."""
        assert map_loyalty_segment(None) == "Unknown"


class TestCalculateLineTotalWithDiscount:
    """Tests for calculate_line_total_with_discount function."""

    def test_batch_of_customer_order_rows(self):
        """Business-like input rows should map to the expected line totals and discounts."""
        order_rows = [
            {"price_cents": 1500, "quantity": 2, "promo_disc_pct": None},
            {"price_cents": 2500, "quantity": 3, "promo_disc_pct": 0.10},
            {"price_cents": 999, "quantity": 1, "promo_disc_pct": 0.25},
        ]

        totals = [
            calculate_line_total_with_discount(row["price_cents"], row["quantity"], row["promo_disc_pct"])
            for row in order_rows
        ]

        assert totals == [
            (Decimal("30.00"), Decimal("0.00")),
            (Decimal("75.00"), Decimal("7.50")),
            (Decimal("9.99"), Decimal("2.50")),
        ]

    def test_no_discount(self):
        """Test calculation with no discount."""
        total, discount = calculate_line_total_with_discount(1500, 2, None)
        assert total == Decimal("30.00")
        assert discount == Decimal("0.00")
    
    def test_with_10_percent_discount(self):
        """Test calculation with 10% discount."""
        # $15.00 × 2 = $30.00, 10% discount = $3.00
        total, discount = calculate_line_total_with_discount(1500, 2, 0.10)
        assert total == Decimal("30.00")
        assert discount == Decimal("3.00")
    
    def test_with_25_percent_discount(self):
        """Test calculation with 25% discount."""
        # $20.00 × 1 = $20.00, 25% discount = $5.00
        total, discount = calculate_line_total_with_discount(2000, 1, 0.25)
        assert total == Decimal("20.00")
        assert discount == Decimal("5.00")
    
    def test_single_quantity(self):
        """Test calculation with quantity of 1."""
        total, discount = calculate_line_total_with_discount(999, 1, None)
        assert total == Decimal("9.99")
        assert discount == Decimal("0.00")
    
    def test_large_quantity(self):
        """Test calculation with large quantity."""
        total, discount = calculate_line_total_with_discount(100, 100, None)
        assert total == Decimal("100.00")
        assert discount == Decimal("0.00")
    
    def test_zero_discount(self):
        """Test calculation with explicit zero discount."""
        total, discount = calculate_line_total_with_discount(1500, 2, 0.0)
        assert total == Decimal("30.00")
        assert discount == Decimal("0.00")
    
    def test_price_none_raises_error(self):
        """Test that None price raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            calculate_line_total_with_discount(None, 2, None)
    
    def test_quantity_none_raises_error(self):
        """Test that None quantity raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            calculate_line_total_with_discount(1500, None, None)
    
    def test_negative_price_raises_error(self):
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_line_total_with_discount(-100, 2, None)
    
    def test_negative_quantity_raises_error(self):
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_line_total_with_discount(1500, -1, None)