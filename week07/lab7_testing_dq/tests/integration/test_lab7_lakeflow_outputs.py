import pytest

pytestmark = pytest.mark.integration


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
        AND try_cast(loyalty_segment AS INT) IS NOT NULL
        AND try_cast(loyalty_segment AS INT) BETWEEN 0 AND 3
        AND try_cast(units_purchased AS DOUBLE) IS NOT NULL
        AND try_cast(units_purchased AS DOUBLE) >= 0
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
        OR try_cast(loyalty_segment AS INT) IS NULL
        OR try_cast(loyalty_segment AS INT) NOT BETWEEN 0 AND 3
        OR try_cast(units_purchased AS DOUBLE) IS NULL
        OR try_cast(units_purchased AS DOUBLE) < 0
    """


def _order_valid_predicate() -> str:
    return """
        order_number IS NOT NULL
        AND customer_id IS NOT NULL
        AND TRIM(CAST(customer_id AS STRING)) <> ''
        AND number_of_line_items IS NOT NULL
        AND try_cast(number_of_line_items AS INT) > 0
        AND order_datetime IS NOT NULL
        AND TRIM(CAST(order_datetime AS STRING)) <> ''
    """


def _order_invalid_predicate() -> str:
    return """
        order_number IS NULL
        OR customer_id IS NULL
        OR TRIM(CAST(customer_id AS STRING)) = ''
        OR number_of_line_items IS NULL
        OR try_cast(number_of_line_items AS INT) <= 0
        OR order_datetime IS NULL
        OR TRIM(CAST(order_datetime AS STRING)) = ''
    """


def test_lab7_customer_valid_and_quarantine_branch_counts_are_consistent(spark, catalog, bronze_schema, silver_schema):

    bronze = spark.table(f"{catalog}.{bronze_schema}.brz_customers")
    valid = spark.table(f"{catalog}.{silver_schema}.slv_customers_lab7_valid")
    quarantine = spark.table(f"{catalog}.{silver_schema}.slv_customers_lab7_quarantine")

    assert valid.count() + quarantine.count() == bronze.count()
    assert valid.filter(_customer_valid_predicate()).count() == valid.count()
    assert quarantine.filter(_customer_invalid_predicate()).count() == quarantine.count()
    assert quarantine.filter("failure_reason IS NOT NULL AND TRIM(failure_reason) <> ''").count() == quarantine.count()


def test_lab7_order_valid_and_quarantine_branch_counts_are_consistent(spark, catalog, bronze_schema, silver_schema):

    bronze = spark.table(f"{catalog}.{bronze_schema}.brz_sales_orders")
    valid = spark.table(f"{catalog}.{silver_schema}.slv_sales_orders_lab7_valid")
    quarantine = spark.table(f"{catalog}.{silver_schema}.slv_sales_orders_lab7_quarantine")

    assert valid.count() + quarantine.count() == bronze.count()
    assert valid.filter(_order_valid_predicate()).count() == valid.count()
    assert quarantine.filter(_order_invalid_predicate()).count() == quarantine.count()
    assert quarantine.filter("failure_reason IS NOT NULL AND TRIM(failure_reason) <> ''").count() == quarantine.count()
