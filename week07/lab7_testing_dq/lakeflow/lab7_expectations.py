"""Pure-Python validation helpers for the Lab 7 Lakeflow quality rules."""

from __future__ import annotations


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def customer_rule_violations(row):
    """Return a list of failed customer validation reasons for a Bronze-sourced row."""
    errors = []

    if _is_missing(row.get("customer_id")):
        errors.append("customer_id is null")
    if _is_missing(row.get("state")):
        errors.append("state is null")
    if _is_missing(row.get("city")):
        errors.append("city is null")
    if _is_missing(row.get("valid_from")):
        errors.append("valid_from_ts is null")

    try:
        loyalty_segment = int(row.get("loyalty_segment")) if row.get("loyalty_segment") is not None else None
    except (TypeError, ValueError):
        loyalty_segment = None
    if loyalty_segment is None or loyalty_segment < 0 or loyalty_segment > 3:
        errors.append("loyalty_segment out of range")

    try:
        units_purchased = float(row.get("units_purchased")) if row.get("units_purchased") is not None else None
    except (TypeError, ValueError):
        units_purchased = None
    if units_purchased is None or units_purchased < 0:
        errors.append("units_purchased < 0")

    return errors


def order_rule_violations(row):
    """Return a list of failed order validation reasons for a Bronze-sourced row."""
    errors = []

    if _is_missing(row.get("order_number")):
        errors.append("order_number is null")
    if _is_missing(row.get("customer_id")):
        errors.append("customer_id is null")

    try:
        line_items = int(row.get("number_of_line_items")) if row.get("number_of_line_items") is not None else None
    except (TypeError, ValueError):
        line_items = None
    if line_items is None or line_items <= 0:
        errors.append("line_items <= 0")

    if _is_missing(row.get("order_datetime")):
        errors.append("order_ts is null")

    return errors
