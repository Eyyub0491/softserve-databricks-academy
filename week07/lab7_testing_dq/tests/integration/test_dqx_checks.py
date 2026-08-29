import os

import pytest
from databricks.connect import DatabricksSession

from dq.dqx_checks import (
    run_dqx_customer_validation,
    run_dqx_fact_reference_validation,
)

pytestmark = pytest.mark.integration


def _require_databricks_runtime() -> None:
    if os.environ.get("DATABRICKS_RUN_INTEGRATION", "0") != "1":
        pytest.skip("Integration tests are disabled; set DATABRICKS_RUN_INTEGRATION=1 to run them.")


def test_dqx_customer_rules_flag_real_duplicates():
    _require_databricks_runtime()
    spark = DatabricksSession.builder.serverless().getOrCreate()

    customer_df = spark.table("lab5.silver.slv_customers_clean")
    valid_df, invalid_df = run_dqx_customer_validation(spark, customer_df)

    assert invalid_df.count() > 0
    assert valid_df.count() + invalid_df.count() == customer_df.count()
    assert invalid_df.filter("_errors is not null").count() > 0


def test_dqx_fact_reference_rules_flag_missing_dimension_keys():
    _require_databricks_runtime()
    spark = DatabricksSession.builder.serverless().getOrCreate()

    fact_df = spark.table("lab5.gold.fct_sales_orders")
    ref_dfs = {
        "dim_customers": spark.table("lab5.gold.dim_customers"),
        "dim_products": spark.table("lab5.gold.dim_products"),
        "dim_date": spark.table("lab5.gold.dim_date"),
    }

    valid_df, invalid_df = run_dqx_fact_reference_validation(spark, fact_df, ref_dfs)

    assert invalid_df.count() > 0
    assert valid_df.count() + invalid_df.count() == fact_df.count()
    assert invalid_df.filter("_errors is not null").count() > 0
