import os

import pytest

from dq.checks import (
    check_completeness,
    check_referential_integrity,
    check_unique,
    check_reconciliation,
)
from dq.databricks import execute_sql

pytestmark = pytest.mark.integration


def _require_databricks_sql() -> None:
    if os.environ.get("DATABRICKS_RUN_INTEGRATION", "0") != "1":
        pytest.skip("Integration tests are disabled; set DATABRICKS_RUN_INTEGRATION=1 to run them.")


def _fetch_rows(query: str):
    _require_databricks_sql()
    return execute_sql(query)


def test_bronze_to_silver_customer_count_and_completeness():
    bronze_count = _fetch_rows("SELECT COUNT(*) AS row_count FROM lab5.bronze.brz_customers")[0]["row_count"]
    silver_count = _fetch_rows("SELECT COUNT(*) AS row_count FROM lab5.silver.slv_customers_clean")[0]["row_count"]

    assert bronze_count == silver_count, (
        f"Bronze-to-Silver customer row counts differ: bronze={bronze_count}, silver={silver_count}"
    )

    rows = _fetch_rows(
        "SELECT customer_id, state, loyalty_segment FROM lab5.silver.slv_customers_clean LIMIT 1000"
    )
    result = check_completeness(rows, ["customer_id", "state", "loyalty_segment"])
    assert result.passed, f"Customer completeness failed: {result.details}"


def test_silver_customer_uniqueness():
    rows = _fetch_rows("SELECT customer_id FROM lab5.silver.slv_customers_clean")
    result = check_unique(rows, ["customer_id"])

    assert not result.passed, (
        "Expected duplicate customer IDs in the silver layer, because the live dataset contains "
        f"duplicate keys: {result.violations[:5]}"
    )
    assert len(result.violations) > 0


def test_gold_fact_primary_key_uniqueness():
    rows = _fetch_rows("SELECT order_line_key FROM lab5.gold.fct_sales_orders")
    result = check_unique(rows, ["order_line_key"])
    assert result.passed, f"Fact primary-key uniqueness failed: {result.violations}"


def test_gold_fact_customer_reference_integrity():
    child_rows = _fetch_rows("SELECT DISTINCT customer_key FROM lab5.gold.fct_sales_orders")
    parent_rows = _fetch_rows("SELECT customer_key FROM lab5.gold.dim_customers")
    result = check_referential_integrity(child_rows, "customer_key", parent_rows, "customer_key")

    assert not result.passed, (
        "Expected broken customer foreign keys in the gold fact table; live data contains missing "
        f"dim_customers rows: {result.violations[:10]}"
    )
    assert len(result.violations) > 0


def test_gold_fact_product_reference_integrity():
    child_rows = _fetch_rows("SELECT DISTINCT product_key FROM lab5.gold.fct_sales_orders")
    parent_rows = _fetch_rows("SELECT product_key FROM lab5.gold.dim_products")
    result = check_referential_integrity(child_rows, "product_key", parent_rows, "product_key")
    assert result.passed, f"Gold fact -> product FK integrity failed: {result.violations[:10]}"


def test_gold_fact_date_reference_integrity():
    child_rows = _fetch_rows("SELECT DISTINCT date_key FROM lab5.gold.fct_sales_orders")
    parent_rows = _fetch_rows("SELECT date_key FROM lab5.gold.dim_date")
    result = check_referential_integrity(child_rows, "date_key", parent_rows, "date_key")
    assert result.passed, f"Gold fact -> date FK integrity failed: {result.violations[:10]}"


def test_gold_reconciliation_matches_lab6_validation_logic():
    fact_rows = _fetch_rows(
        "SELECT COUNT(DISTINCT order_number) AS total_orders, ROUND(SUM(line_total), 2) AS revenue "
        "FROM lab5.gold.fct_sales_orders"
    )
    customer_rows = _fetch_rows(
        "SELECT SUM(total_orders) AS total_orders, ROUND(SUM(total_revenue), 2) AS revenue "
        "FROM lab5.gold.agg_customer_summary"
    )
    daily_rows = _fetch_rows(
        "SELECT SUM(total_orders) AS total_orders, ROUND(SUM(total_revenue), 2) AS revenue "
        "FROM lab5.gold.agg_daily_sales"
    )

    fact = fact_rows[0]
    customer = customer_rows[0]
    daily = daily_rows[0]

    assert fact["total_orders"] == customer["total_orders"] == daily["total_orders"], (
        "Gold reconciliation failed: order totals differ between fact and aggregates. "
        f"fact={fact}, customer={customer}, daily={daily}"
    )

    tolerance = 0.01
    assert abs(float(fact["revenue"]) - float(customer["revenue"])) <= tolerance, (
        "Gold reconciliation failed: fact revenue differs from customer summary revenue. "
        f"fact={fact}, customer={customer}"
    )

    result = check_reconciliation(
        actual_count=fact["total_orders"],
        expected_count=customer["total_orders"],
        tolerance=0,
        actual_total=fact["revenue"],
        expected_total=customer["revenue"],
        )
    assert result.passed, f"Gold reconciliation check failed: {result.details}"
