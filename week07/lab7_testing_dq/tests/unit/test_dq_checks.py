from datetime import datetime, timedelta

import pytest

from dq.checks import (
    DQResult,
    check_completeness,
    check_freshness,
    check_numeric_range,
    check_referential_integrity,
    check_reconciliation,
    check_unique,
    check_valid_values,
)


def test_completeness_passes_for_required_fields():
    rows = [
        {"customer_id": "C1", "state": "CA", "loyalty_segment": 1},
        {"customer_id": "C2", "state": "NY", "loyalty_segment": 2},
    ]

    result = check_completeness(rows, ["customer_id", "state", "loyalty_segment"])

    assert isinstance(result, DQResult)
    assert result.passed is True
    assert result.details == {}


def test_completeness_fails_for_missing_required_values():
    rows = [
        {"customer_id": "C1", "state": "CA", "loyalty_segment": 1},
        {"customer_id": None, "state": "NY", "loyalty_segment": None},
    ]

    result = check_completeness(rows, ["customer_id", "loyalty_segment"])

    assert result.passed is False
    assert "customer_id" in result.details
    assert "loyalty_segment" in result.details


def test_unique_passes_for_distinct_keys():
    rows = [
        {"customer_id": "C1", "state": "CA"},
        {"customer_id": "C2", "state": "NY"},
    ]

    result = check_unique(rows, ["customer_id"])

    assert result.passed is True
    assert result.violations == []


def test_unique_fails_for_duplicate_keys():
    rows = [
        {"customer_id": "C1", "state": "CA"},
        {"customer_id": "C1", "state": "WA"},
        {"customer_id": "C2", "state": "NY"},
    ]

    result = check_unique(rows, ["customer_id"])

    assert result.passed is False
    assert result.violations == [{"customer_id": "C1", "count": 2}]


def test_unique_supports_composite_keys():
    rows = [
        {"customer_id": "C1", "order_number": 101},
        {"customer_id": "C1", "order_number": 101},
        {"customer_id": "C2", "order_number": 101},
    ]

    result = check_unique(rows, ["customer_id", "order_number"])

    assert result.passed is False
    assert any(v["customer_id"] == "C1" and v["order_number"] == 101 for v in result.violations)


def test_valid_values_passes_for_accepted_values():
    rows = [
        {"state": "CA"},
        {"state": "NY"},
        {"state": "TX"},
    ]

    result = check_valid_values(rows, "state", {"CA", "NY", "TX"})

    assert result.passed is True


def test_valid_values_fails_for_disallowed_values():
    rows = [
        {"state": "CA"},
        {"state": "ZZ"},
    ]

    result = check_valid_values(rows, "state", {"CA", "NY", "TX"})

    assert result.passed is False
    assert result.violations == [{"state": "ZZ"}]


def test_numeric_range_passes_for_valid_values():
    rows = [
        {"loyalty_segment": 1},
        {"loyalty_segment": 2},
        {"loyalty_segment": 3},
    ]

    result = check_numeric_range(rows, "loyalty_segment", min_value=0, max_value=3)

    assert result.passed is True


def test_numeric_range_fails_outside_bounds():
    rows = [
        {"loyalty_segment": 0},
        {"loyalty_segment": 4},
    ]

    result = check_numeric_range(rows, "loyalty_segment", min_value=0, max_value=3)

    assert result.passed is False
    assert result.violations == [{"loyalty_segment": 4}]


def test_referential_integrity_passes_when_child_keys_exist():
    parents = [{"customer_id": "C1"}, {"customer_id": "C2"}]
    children = [{"customer_id": "C1"}, {"customer_id": "C2"}]

    result = check_referential_integrity(children, "customer_id", parents, "customer_id")

    assert result.passed is True


def test_referential_integrity_fails_for_missing_parents():
    parents = [{"customer_id": "C1"}]
    children = [{"customer_id": "C1"}, {"customer_id": "C2"}]

    result = check_referential_integrity(children, "customer_id", parents, "customer_id")

    assert result.passed is False
    assert result.violations == ["C2"]


def test_freshness_passes_when_timestamp_is_recent():
    now = datetime(2024, 1, 10, 12, 0, 0)
    timestamp = now - timedelta(minutes=5)

    result = check_freshness(timestamp, max_age_minutes=30, now=now)

    assert result.passed is True


def test_freshness_fails_when_timestamp_is_too_old():
    now = datetime(2024, 1, 10, 12, 0, 0)
    timestamp = now - timedelta(minutes=45)

    result = check_freshness(timestamp, max_age_minutes=30, now=now)

    assert result.passed is False
    assert "age_minutes" in result.details


def test_reconciliation_matches_row_counts_within_tolerance():
    result = check_reconciliation(actual_count=10, expected_count=9, tolerance=1)

    assert result.passed is True


def test_reconciliation_fails_when_counts_exceed_tolerance():
    result = check_reconciliation(actual_count=10, expected_count=7, tolerance=1)

    assert result.passed is False
    assert result.details["difference"] == 3


def test_reconciliation_matches_numeric_aggregate_with_tolerance():
    result = check_reconciliation(actual_total=100.0, expected_total=99.5, tolerance=0.6)

    assert result.passed is True


def test_empty_collection_is_handled_safely():
    result = check_completeness([], ["customer_id"])
    assert result.passed is True

    result = check_unique([], ["customer_id"])
    assert result.passed is True

    result = check_referential_integrity([], "customer_id", [], "customer_id")
    assert result.passed is True


def test_invalid_row_values_are_handled_safely():
    rows = [{"customer_id": "C1"}, {"customer_id": None}]
    result = check_completeness(rows, ["customer_id"]) 
    assert result.passed is False

    result = check_valid_values(rows, "customer_id", {"C1"})
    assert result.passed is False
