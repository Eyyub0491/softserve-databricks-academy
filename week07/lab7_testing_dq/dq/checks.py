"""Generic local data-quality checks for lab7 testing.

These helpers are intentionally pure Python and deterministic so they can
exercise DataFrame-like records or list-of-dicts before any Databricks/Spark
execution is added.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, List, Optional, Sequence, Set, Tuple, Union


@dataclass
class DQResult:
    """Simple result object for a DQ check."""

    passed: bool
    details: dict = field(default_factory=dict)
    violations: List[Any] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.passed


def _normalise_value(value: Any) -> Any:
    """Normalize empty-like values that should be treated as missing."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _key_tuple(record: dict, key_fields: Sequence[str]) -> tuple:
    values = []
    for field in key_fields:
        value = _normalise_value(record.get(field))
        values.append(value)
    return tuple(values)


def check_completeness(
    rows: Iterable[dict],
    required_fields: Sequence[str],
) -> DQResult:
    """Return True when all required fields are populated for every record.

    A field is considered missing if it is None or an empty string after trimming.
    """
    rows = list(rows or [])
    if not rows:
        return DQResult(passed=True, details={})

    failures: dict[str, list[str]] = {field: [] for field in required_fields}

    for index, row in enumerate(rows):
        if row is None:
            for field in required_fields:
                failures[field].append(f"row {index}: record is None")
            continue

        for field in required_fields:
            value = _normalise_value(row.get(field))
            if value is None:
                failures[field].append(f"row {index}: missing '{field}'")

    details = {
        field: messages for field, messages in failures.items() if messages
    }
    return DQResult(passed=not bool(details), details=details)


def check_unique(
    rows: Iterable[dict],
    key_fields: Sequence[str],
) -> DQResult:
    """Detect duplicate values for a single key or a composite key.

    Returns a DQResult with `violations` containing repeated key values and counts.
    """
    rows = list(rows or [])
    if not rows:
        return DQResult(passed=True, violations=[])

    counts: dict[tuple, int] = defaultdict(int)
    seen: dict[tuple, Any] = {}

    for row in rows:
        if row is None:
            continue
        key = _key_tuple(row, key_fields)
        counts[key] += 1
        if counts[key] == 2:
            seen[key] = key

    violations = []
    for key in sorted(counts.keys(), key=lambda item: item):
        count = counts[key]
        if count > 1:
            violation = {
                field: value for field, value in zip(key_fields, key)
            }
            violation["count"] = count
            violations.append(violation)

    return DQResult(passed=not bool(violations), violations=violations)


def check_valid_values(
    rows: Iterable[dict],
    field_name: str,
    allowed_values: Set[Any],
) -> DQResult:
    """Verify that every value in a field belongs to an accepted set."""
    rows = list(rows or [])
    if not rows:
        return DQResult(passed=True, violations=[])

    violations = []
    for row in rows:
        if row is None:
            continue
        value = _normalise_value(row.get(field_name))
        if value is None or value not in allowed_values:
            violations.append({field_name: value})

    return DQResult(passed=not bool(violations), violations=violations)


def check_numeric_range(
    rows: Iterable[dict],
    field_name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> DQResult:
    """Verify numeric values are within an inclusive range."""
    rows = list(rows or [])
    if not rows:
        return DQResult(passed=True, violations=[])

    violations = []
    for row in rows:
        if row is None:
            continue
        value = row.get(field_name)
        if value is None or value == "":
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            violations.append({field_name: value})
            continue

        if min_value is not None and numeric < min_value:
            violations.append({field_name: value})
            continue
        if max_value is not None and numeric > max_value:
            violations.append({field_name: value})

    return DQResult(passed=not bool(violations), violations=violations)


def check_referential_integrity(
    child_rows: Iterable[dict],
    child_key_field: str,
    parent_rows: Iterable[dict],
    parent_key_field: str,
) -> DQResult:
    """Verify each child key exists in the parent collection.

    All values are normalized so None/blank values are ignored in the parent and
    flagged as missing in the child.
    """
    child_rows = list(child_rows or [])
    parent_rows = list(parent_rows or [])

    if not child_rows:
        return DQResult(passed=True, violations=[])

    parent_keys = {
        _normalise_value(row.get(parent_key_field))
        for row in parent_rows
        if _normalise_value(row.get(parent_key_field)) is not None
    }

    violations = []
    for row in child_rows:
        if row is None:
            continue
        value = _normalise_value(row.get(child_key_field))
        if value is None:
            continue
        if value not in parent_keys:
            violations.append(value)

    return DQResult(passed=not bool(violations), violations=violations)


def check_freshness(
    latest_value: Optional[datetime],
    max_age_minutes: float,
    now: Optional[datetime] = None,
) -> DQResult:
    """Check whether a timestamp is within a configured freshness window."""
    if latest_value is None:
        return DQResult(
            passed=False,
            details={"reason": "timestamp is missing", "max_age_minutes": max_age_minutes},
        )

    if now is None:
        now = datetime.utcnow()

    age_minutes = (now - latest_value).total_seconds() / 60.0
    passed = age_minutes <= max_age_minutes
    details = {
        "latest_value": latest_value,
        "now": now,
        "age_minutes": round(age_minutes, 2),
        "max_age_minutes": max_age_minutes,
    }
    return DQResult(passed=passed, details=details)


def check_reconciliation(
    actual_count: Optional[float] = None,
    expected_count: Optional[float] = None,
    tolerance: float = 0,
    actual_total: Optional[float] = None,
    expected_total: Optional[float] = None,
) -> DQResult:
    """Compare counts or aggregates with a configurable tolerance.

    This helper is intentionally generic. Use either count comparison or total
    comparison depending on the use case; both can be checked in one call if
    needed.
    """
    details: dict[str, Any] = {}

    if actual_count is not None and expected_count is not None:
        difference = abs(float(actual_count) - float(expected_count))
        details["count_difference"] = difference
        details["count_tolerance"] = tolerance
        details["actual_count"] = actual_count
        details["expected_count"] = expected_count
        count_passed = difference <= tolerance
    else:
        count_passed = True

    if actual_total is not None and expected_total is not None:
        total_difference = abs(float(actual_total) - float(expected_total))
        details["total_difference"] = total_difference
        details["total_tolerance"] = tolerance
        details["actual_total"] = actual_total
        details["expected_total"] = expected_total
        total_passed = total_difference <= tolerance
    else:
        total_passed = True

    passed = count_passed and total_passed
    if not passed:
        details["difference"] = details.get("count_difference", details.get("total_difference"))
    return DQResult(passed=passed, details=details)
