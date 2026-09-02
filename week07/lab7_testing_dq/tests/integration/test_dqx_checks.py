import pytest

from dq.dqx_checks import (
    run_dqx_customer_validation,
    run_dqx_fact_reference_validation,
)

pytestmark = pytest.mark.integration


def test_dqx_customer_rules_flag_silver_violations(spark, catalog, silver_schema):

    customer_df = spark.table(f"{catalog}.{silver_schema}.slv_customers_clean")
    valid_df, invalid_df = run_dqx_customer_validation(spark, customer_df)

    assert invalid_df.count() > 0
    assert valid_df.count() + invalid_df.count() == customer_df.count()
    assert invalid_df.filter("_errors is not null").count() > 0


def test_dqx_fact_reference_rules_pass_for_consistent_gold(spark, catalog, gold_schema):

    fact_df = spark.table(f"{catalog}.{gold_schema}.fct_sales_orders")
    ref_dfs = {
        "dim_customers": spark.table(f"{catalog}.{gold_schema}.dim_customers"),
        "dim_products": spark.table(f"{catalog}.{gold_schema}.dim_products"),
        "dim_date": spark.table(f"{catalog}.{gold_schema}.dim_date"),
    }

    valid_df, invalid_df = run_dqx_fact_reference_validation(spark, fact_df, ref_dfs)

    assert invalid_df.count() == 0
    assert valid_df.count() + invalid_df.count() == fact_df.count()
    assert invalid_df.filter("_errors is not null").count() == 0
