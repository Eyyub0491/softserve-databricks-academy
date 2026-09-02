import os
from datetime import datetime

import pytest
from databricks.connect import DatabricksSession

from dq.checks import check_freshness

pytestmark = pytest.mark.integration


def _require_databricks_runtime() -> None:
    if os.environ.get("DATABRICKS_RUN_INTEGRATION", "0") != "1":
        pytest.skip("Integration tests are disabled; set DATABRICKS_RUN_INTEGRATION=1 to run them.")


def test_customer_branch_reconciliation():
    _require_databricks_runtime()
    spark = DatabricksSession.builder.serverless().getOrCreate()

    bronze = spark.table("lab5.bronze.brz_customers")
    valid = spark.table("lab5.silver.slv_customers_lab7_valid")
    quarantine = spark.table("lab5.silver.slv_customers_lab7_quarantine")

    assert valid.count() + quarantine.count() == bronze.count()
    assert quarantine.filter("failure_reason IS NOT NULL AND TRIM(failure_reason) <> ''").count() == quarantine.count()
    assert valid.filter(
        "customer_id IS NOT NULL AND TRIM(CAST(customer_id AS STRING)) <> '' "
        "AND state IS NOT NULL AND TRIM(CAST(state AS STRING)) <> '' "
        "AND city IS NOT NULL AND TRIM(CAST(city AS STRING)) <> '' "
        "AND valid_from IS NOT NULL AND TRIM(CAST(valid_from AS STRING)) <> '' "
        "AND CAST(loyalty_segment AS INT) BETWEEN 0 AND 3 "
        "AND CAST(units_purchased AS DOUBLE) >= 0"
    ).count() == valid.count()

    latest_valid_from = spark.sql(
        "SELECT MAX(CAST(valid_from AS BIGINT)) AS latest_valid_from FROM lab5.bronze.brz_customers"
    ).collect()[0]["latest_valid_from"]
    if latest_valid_from is not None:
        freshness = check_freshness(
            datetime.fromtimestamp(int(latest_valid_from)),
            max_age_minutes=10080,
            now=datetime.utcnow(),
        )
        assert freshness.passed is True


def test_order_branch_reconciliation():
    _require_databricks_runtime()
    spark = DatabricksSession.builder.serverless().getOrCreate()

    bronze = spark.table("lab5.bronze.brz_sales_orders")
    valid = spark.table("lab5.silver.slv_sales_orders_lab7_valid")
    quarantine = spark.table("lab5.silver.slv_sales_orders_lab7_quarantine")

    assert valid.count() + quarantine.count() == bronze.count()
    assert quarantine.filter("failure_reason IS NOT NULL AND TRIM(failure_reason) <> ''").count() == quarantine.count()
    assert valid.filter(
        "order_number IS NOT NULL AND customer_id IS NOT NULL "
        "AND TRIM(CAST(customer_id AS STRING)) <> '' "
        "AND CAST(number_of_line_items AS INT) > 0 "
        "AND order_datetime IS NOT NULL"
    ).count() == valid.count()
