from lakeflow.lab7_expectations import customer_rule_violations, order_rule_violations


def test_customer_rule_violations_flags_invalid_rows():
    valid = {
        "customer_id": "CUST-001",
        "state": "WA",
        "city": "Seattle",
        "valid_from": "1704067200",
        "loyalty_segment": 2,
        "units_purchased": 5,
    }
    invalid = {
        "customer_id": None,
        "state": None,
        "city": "Seattle",
        "valid_from": "",
        "loyalty_segment": 9,
        "units_purchased": -1,
    }

    assert customer_rule_violations(valid) == []
    violations = customer_rule_violations(invalid)
    assert "customer_id is null" in violations
    assert "state is null" in violations
    assert "valid_from_ts is null" in violations
    assert "loyalty_segment out of range" in violations
    assert "units_purchased < 0" in violations


def test_order_rule_violations_flags_invalid_rows():
    valid = {
        "order_number": 1001,
        "customer_id": "CUST-001",
        "number_of_line_items": "3",
        "order_datetime": "1704067200",
    }
    invalid = {
        "order_number": None,
        "customer_id": "",
        "number_of_line_items": "0",
        "order_datetime": None,
    }

    assert order_rule_violations(valid) == []
    violations = order_rule_violations(invalid)
    assert "order_number is null" in violations
    assert "customer_id is null" in violations
    assert "line_items <= 0" in violations
    assert "order_ts is null" in violations
