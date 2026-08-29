import os

import pytest
from databricks.connect import DatabricksSession

pytestmark = pytest.mark.integration


def _require_databricks_runtime() -> None:
    if os.environ.get("DATABRICKS_RUN_INTEGRATION", "0") != "1":
        pytest.skip("Integration tests are disabled; set DATABRICKS_RUN_INTEGRATION=1 to run them.")


def _customer_valid_predicate() -> str:
    return """
        customer_id IS NOT NULL
        AND TRIM(CAST(customer_id AS STRING)) <> ''
        AND state IS NOT NULL
        AND TRIM(CAST(state AS STRING)) <> ''
        AND city IS NOT NULL
        AND TRIM(CAST(city AS STRING)) <> ''
        AND valid_from IS NOT NULL
        AND TRIM(CAST(valid_from AS STRING)) <> ''
        AND CAST(loyalty_segment AS INT) IS NOT NULL
        AND CAST(loyalty_segment AS INT) BETWEEN 0 AND 3
        AND CAST(units_purchased AS DOUBLE) IS NOT NULL
        AND CAST(units_purchased AS DOUBLE) >= 0
    """


def _customer_invalid_predicate() -> str:
    return """
        customer_id IS NULL
        OR TRIM(CAST(customer_id AS STRING)) = ''
        OR state IS NULL
        OR TRIM(CAST(state AS STRING)) = ''
        OR city IS NULL
        OR TRIM(CAST(city AS STRING)) = ''
        OR valid_from IS NULL
        OR TRIM(CAST(valid_from AS STRING)) = ''
        OR CAST(loyalty_segment AS INT) IS NULL
        OR CAST(loyalty_segment AS INT) NOT BETWEEN 0 AND 3
        OR CAST(units_purchased AS DOUBLE) IS NULL
        OR CAST(units_purchased AS DOUBLE) < 0
    """


def _order_valid_predicate() -> str:
    return """
        order_number IS NOT NULL
        AND customer_id IS NOT NULL
        AND TRIM(CAST(customer_id AS STRING)) <> ''
        AND number_of_line_items IS NOT NULL
        AND CAST(number_of_line_items AS INT) > 0
        AND order_datetime IS NOT NULL
        AND TRIM(CAST(order_datetime AS STRING)) <> ''
    """


def _order_invalid_predicate() -> str:
    return """
        order_number IS NULL
        OR customer_id IS NULL
        OR TRIM(CAST(customer_id AS STRING)) = ''
        OR number_of_line_items IS NULL
        OR CAST(number_of_line_items AS INT) <= 0
        OR order_datetime IS NULL
        OR TRIM(CAST(order_datetime AS STRING)) = ''
    """


def test_lab7_customer_valid_and_quarantine_branch_counts_are_consistent():
    _require_databricks_runtime()
    spark = DatabricksSession.builder.serverless().getOrCreate()

    bronze = spark.table("lab5.bronze.brz_customers")
    valid = spark.table("lab5.silver.slv_customers_lab7_valid")
    quarantine = spark.table("lab5.silver.slv_customers_lab7_quarantine")

    assert valid.count() + quarantine.count() == bronze.count()
    assert valid.filter(_customer_valid_predicate()).count() == valid.count()
    assert quarantine.filter(_customer_invalid_predicate()).count() == quarantine.count()
    assert quarantine.filter("failure_reason IS NOT NULL AND TRIM(failure_reason) <> ''").count() == quarantine.count()


def test_lab7_order_valid_and_quarantine_branch_counts_are_consistent():
    _require_databricks_runtime()
    spark = DatabricksSession.builder.serverless().getOrCreate()

    bronze = spark.table("lab5.bronze.brz_sales_orders")
    valid = spark.table("lab5.silver.slv_sales_orders_lab7_valid")
    quarantine = spark.table("lab5.silver.slv_sales_orders_lab7_quarantine")

    assert valid.count() + quarantine.count() == bronze.count()
    assert valid.filter(_order_valid_predicate()).count() == valid.count()
    assert quarantine.filter(_order_invalid_predicate()).count() == quarantine.count()
    assert quarantine.filter("failure_reason IS NOT NULL AND TRIM(failure_reason) <> ''").count() == quarantine.count()
