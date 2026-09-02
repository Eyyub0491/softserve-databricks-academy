import pytest

pytestmark = pytest.mark.integration


def test_customer_branch_reconciliation(spark, catalog, bronze_schema, silver_schema):

    bronze = spark.table(f"{catalog}.{bronze_schema}.brz_customers")
    valid = spark.table(f"{catalog}.{silver_schema}.slv_customers_lab7_valid")
    quarantine = spark.table(f"{catalog}.{silver_schema}.slv_customers_lab7_quarantine")

    assert valid.count() + quarantine.count() == bronze.count()
    assert quarantine.filter("failure_reason IS NOT NULL AND TRIM(failure_reason) <> ''").count() == quarantine.count()
    assert valid.filter(
        "customer_id IS NOT NULL AND TRIM(CAST(customer_id AS STRING)) <> '' "
        "AND state IS NOT NULL AND TRIM(CAST(state AS STRING)) <> '' "
        "AND city IS NOT NULL AND TRIM(CAST(city AS STRING)) <> '' "
        "AND valid_from IS NOT NULL AND TRIM(CAST(valid_from AS STRING)) <> '' "
        "AND try_cast(loyalty_segment AS INT) BETWEEN 0 AND 3 "
        "AND try_cast(units_purchased AS DOUBLE) IS NOT NULL "
        "AND try_cast(units_purchased AS DOUBLE) >= 0"
    ).count() == valid.count()

    ingestion_timestamp = spark.sql(
        f"SELECT MAX(ingestion_timestamp) AS latest_ingestion_timestamp FROM {catalog}.{bronze_schema}.brz_customers"
    ).collect()[0]["latest_ingestion_timestamp"]
    assert ingestion_timestamp is not None


def test_order_branch_reconciliation(spark, catalog, bronze_schema, silver_schema):

    bronze = spark.table(f"{catalog}.{bronze_schema}.brz_sales_orders")
    valid = spark.table(f"{catalog}.{silver_schema}.slv_sales_orders_lab7_valid")
    quarantine = spark.table(f"{catalog}.{silver_schema}.slv_sales_orders_lab7_quarantine")

    assert valid.count() + quarantine.count() == bronze.count()
    assert quarantine.filter("failure_reason IS NOT NULL AND TRIM(failure_reason) <> ''").count() == quarantine.count()
    assert valid.filter(
        "order_number IS NOT NULL AND customer_id IS NOT NULL "
        "AND TRIM(CAST(customer_id AS STRING)) <> '' "
        "AND try_cast(number_of_line_items AS INT) > 0 "
        "AND order_datetime IS NOT NULL"
    ).count() == valid.count()
