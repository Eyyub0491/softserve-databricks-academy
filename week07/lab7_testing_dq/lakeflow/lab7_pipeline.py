"""Lab 7 Lakeflow validation layer."""

from __future__ import annotations

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, functions as F


CUSTOMER_VALID_CONDITION = (
    "customer_id IS NOT NULL AND TRIM(CAST(customer_id AS STRING)) <> '' "
    "AND state IS NOT NULL AND TRIM(CAST(state AS STRING)) <> '' "
    "AND city IS NOT NULL AND TRIM(CAST(city AS STRING)) <> '' "
    "AND valid_from IS NOT NULL AND TRIM(CAST(valid_from AS STRING)) <> '' "
    "AND try_cast(loyalty_segment AS INT) BETWEEN 0 AND 3 "
    "AND try_cast(units_purchased AS DOUBLE) IS NOT NULL "
    "AND try_cast(units_purchased AS DOUBLE) >= 0"
)

ORDER_VALID_CONDITION = (
    "order_number IS NOT NULL AND TRIM(CAST(order_number AS STRING)) <> '' "
    "AND customer_id IS NOT NULL AND TRIM(CAST(customer_id AS STRING)) <> '' "
    "AND try_cast(number_of_line_items AS INT) > 0 "
    "AND order_datetime IS NOT NULL AND TRIM(CAST(order_datetime AS STRING)) <> ''"
)


def _get_source_table(table_name: str) -> str:
    """Build fully qualified table name from spark configuration."""
    catalog = spark.conf.get("catalog", "lab5")
    bronze_schema = spark.conf.get("bronze_schema", "bronze")
    return f"{catalog}.{bronze_schema}.{table_name}"


def _is_blank(column_name: str):
    return F.col(column_name).isNull() | (F.trim(F.col(column_name).cast("string")) == "")


def _customer_failure_reason(df: DataFrame) -> DataFrame:
    loyalty_segment_int = F.expr("try_cast(loyalty_segment AS INT)")
    units_purchased_double = F.expr("try_cast(units_purchased AS DOUBLE)")

    return (
        df.withColumn("customer_id_invalid", _is_blank("customer_id"))
        .withColumn("state_invalid", _is_blank("state"))
        .withColumn("city_invalid", _is_blank("city"))
        .withColumn("valid_from_invalid", _is_blank("valid_from"))
        .withColumn(
            "loyalty_segment_invalid",
            loyalty_segment_int.isNull() | (~loyalty_segment_int.between(0, 3)),
        )
        .withColumn(
            "units_purchased_invalid",
            units_purchased_double.isNull() | (units_purchased_double < 0),
        )
        .withColumn(
            "failure_reason",
            F.concat_ws(
                "; ",
                F.when(F.col("customer_id_invalid"), F.lit("customer_id is null or blank")).otherwise(F.lit(None)),
                F.when(F.col("state_invalid"), F.lit("state is null or blank")).otherwise(F.lit(None)),
                F.when(F.col("city_invalid"), F.lit("city is null or blank")).otherwise(F.lit(None)),
                F.when(F.col("valid_from_invalid"), F.lit("valid_from is null or blank")).otherwise(F.lit(None)),
                F.when(
                    F.col("loyalty_segment_invalid"),
                    F.lit("loyalty_segment is null, non-numeric, or outside 0-3"),
                ).otherwise(F.lit(None)),
                F.when(
                    F.col("units_purchased_invalid"),
                    F.lit("units_purchased is null, non-numeric, or < 0"),
                ).otherwise(F.lit(None)),
            ),
        )
    )


def _order_failure_reason(df: DataFrame) -> DataFrame:
    line_items_int = F.expr("try_cast(number_of_line_items AS INT)")

    return (
        df.withColumn("order_number_invalid", _is_blank("order_number"))
        .withColumn("customer_id_invalid", _is_blank("customer_id"))
        .withColumn("line_items_invalid", line_items_int.isNull() | (line_items_int <= 0))
        .withColumn("order_ts_invalid", _is_blank("order_datetime"))
        .withColumn(
            "failure_reason",
            F.concat_ws(
                "; ",
                F.when(F.col("order_number_invalid"), F.lit("order_number is null or blank")).otherwise(F.lit(None)),
                F.when(F.col("customer_id_invalid"), F.lit("customer_id is null or blank")).otherwise(F.lit(None)),
                F.when(
                    F.col("line_items_invalid"),
                    F.lit("number_of_line_items is null, non-numeric, or <= 0"),
                ).otherwise(F.lit(None)),
                F.when(F.col("order_ts_invalid"), F.lit("order_datetime is null or blank")).otherwise(F.lit(None)),
            ),
        )
    )


@dp.table(name="slv_customers_lab7_valid")
@dp.expect_or_drop("valid_lab7_customer_record", CUSTOMER_VALID_CONDITION)
def slv_customers_lab7_valid():
    return spark.read.table(_get_source_table("brz_customers"))


@dp.table(name="slv_customers_lab7_quarantine")
def slv_customers_lab7_quarantine():
    return (
        spark.read.table(_get_source_table("brz_customers"))
        .transform(_customer_failure_reason)
        .filter("failure_reason IS NOT NULL AND failure_reason != ''")
    )


@dp.table(name="slv_sales_orders_lab7_valid")
@dp.expect_or_drop("valid_lab7_order_record", ORDER_VALID_CONDITION)
def slv_sales_orders_lab7_valid():
    return spark.read.table(_get_source_table("brz_sales_orders"))


@dp.table(name="slv_sales_orders_lab7_quarantine")
def slv_sales_orders_lab7_quarantine():
    return (
        spark.read.table(_get_source_table("brz_sales_orders"))
        .transform(_order_failure_reason)
        .filter("failure_reason IS NOT NULL AND failure_reason != ''")
    )
