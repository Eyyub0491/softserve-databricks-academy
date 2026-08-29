import os

import pytest
from databricks.connect import DatabricksSession

pytestmark = pytest.mark.integration


def _require_databricks_runtime() -> None:
    if os.environ.get("DATABRICKS_RUN_INTEGRATION", "0") != "1":
        pytest.skip("Integration tests are disabled; set DATABRICKS_RUN_INTEGRATION=1 to run them.")


def test_gold_fact_dimension_and_aggregate_reconciliation():
    _require_databricks_runtime()
    spark = DatabricksSession.builder.serverless().getOrCreate()

    missing_customer_keys = spark.sql(
        """
        SELECT COUNT(*) AS missing_customer_keys
        FROM lab5.gold.fct_sales_orders f
        LEFT ANTI JOIN lab5.gold.dim_customers d ON f.customer_key = d.customer_key
        """
    ).collect()[0]["missing_customer_keys"]
    missing_product_keys = spark.sql(
        """
        SELECT COUNT(*) AS missing_product_keys
        FROM lab5.gold.fct_sales_orders f
        LEFT ANTI JOIN lab5.gold.dim_products p ON f.product_key = p.product_key
        """
    ).collect()[0]["missing_product_keys"]
    missing_date_keys = spark.sql(
        """
        SELECT COUNT(*) AS missing_date_keys
        FROM lab5.gold.fct_sales_orders f
        LEFT ANTI JOIN lab5.gold.dim_date d ON f.date_key = d.date_key
        """
    ).collect()[0]["missing_date_keys"]

    assert missing_customer_keys == 0
    assert missing_product_keys == 0
    assert missing_date_keys == 0

    fact_revenue = spark.sql(
        "SELECT COALESCE(SUM(revenue), 0) AS total_revenue FROM lab5.gold.fct_sales_orders"
    ).collect()[0]["total_revenue"]
    daily_revenue = spark.sql(
        "SELECT COALESCE(SUM(total_revenue), 0) AS total_revenue FROM lab5.gold.agg_daily_sales"
    ).collect()[0]["total_revenue"]
    customer_revenue = spark.sql(
        "SELECT COALESCE(SUM(total_revenue), 0) AS total_revenue FROM lab5.gold.agg_customer_summary"
    ).collect()[0]["total_revenue"]

    assert abs(float(fact_revenue) - float(daily_revenue)) <= max(1.0, abs(float(fact_revenue)) * 0.01)
    assert abs(float(fact_revenue) - float(customer_revenue)) <= max(1.0, abs(float(fact_revenue)) * 0.05)
