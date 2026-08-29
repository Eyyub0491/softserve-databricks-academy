"""Lab 7 Lakeflow validation layer."""

from __future__ import annotations

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, functions as F


def _customer_failure_reason(df: DataFrame) -> DataFrame:
    return (
        df.withColumn(
            "customer_id_invalid",
            F.col("customer_id").isNull() | F.trim(F.col("customer_id").cast("string")).eqNullSafe(""),
        )
        .withColumn(
            "state_invalid",
            F.col("state").isNull() | F.trim(F.col("state").cast("string")).eqNullSafe(""),
        )
        .withColumn(
            "city_invalid",
            F.col("city").isNull() | F.trim(F.col("city").cast("string")).eqNullSafe(""),
        )
        .withColumn(
            "valid_from_invalid",
            F.col("valid_from").isNull() | F.trim(F.col("valid_from").cast("string")).eqNullSafe(""),
        )
        .withColumn(
            "loyalty_segment_invalid",
            F.col("loyalty_segment").isNull()
            | (F.col("loyalty_segment").cast("int").lt(0) | F.col("loyalty_segment").cast("int").gt(3)),
        )
        .withColumn(
            "units_purchased_invalid",
            F.col("units_purchased").cast("double").isNull() | (F.col("units_purchased").cast("double") < 0),
        )
        .withColumn(
            "failure_reason",
            F.concat_ws(
                "; ",
                F.when(F.col("customer_id_invalid"), F.lit("customer_id is null")).otherwise(F.lit(None)),
                F.when(F.col("state_invalid"), F.lit("state is null")).otherwise(F.lit(None)),
                F.when(F.col("city_invalid"), F.lit("city is null")).otherwise(F.lit(None)),
                F.when(F.col("valid_from_invalid"), F.lit("valid_from_ts is null")).otherwise(F.lit(None)),
                F.when(F.col("loyalty_segment_invalid"), F.lit("loyalty_segment out of range")).otherwise(F.lit(None)),
                F.when(F.col("units_purchased_invalid"), F.lit("units_purchased < 0")).otherwise(F.lit(None)),
            ),
        )
    )


def _order_failure_reason(df: DataFrame) -> DataFrame:
    return (
        df.withColumn(
            "order_number_invalid",
            F.col("order_number").isNull(),
        )
        .withColumn(
            "customer_id_invalid",
            F.col("customer_id").isNull() | F.trim(F.col("customer_id").cast("string")).eqNullSafe(""),
        )
        .withColumn(
            "line_items_invalid",
            F.col("number_of_line_items").isNull() | (F.col("number_of_line_items").cast("int") <= 0),
        )
        .withColumn(
            "order_ts_invalid",
            F.col("order_datetime").isNull() | F.trim(F.col("order_datetime").cast("string")).eqNullSafe(""),
        )
        .withColumn(
            "failure_reason",
            F.concat_ws(
                "; ",
                F.when(F.col("order_number_invalid"), F.lit("order_number is null")).otherwise(F.lit(None)),
                F.when(F.col("customer_id_invalid"), F.lit("customer_id is null")).otherwise(F.lit(None)),
                F.when(F.col("line_items_invalid"), F.lit("line_items <= 0")).otherwise(F.lit(None)),
                F.when(F.col("order_ts_invalid"), F.lit("order_ts is null")).otherwise(F.lit(None)),
            ),
        )
    )


@dp.table(name="slv_customers_lab7_valid")
@dp.expect_or_drop(
    "valid_lab7_customer_record",
    "customer_id IS NOT NULL AND state IS NOT NULL AND city IS NOT NULL AND valid_from IS NOT NULL AND CAST(loyalty_segment AS INT) BETWEEN 0 AND 3 AND CAST(units_purchased AS DOUBLE) >= 0"
)
def slv_customers_lab7_valid():
    return spark.read.table("lab5.bronze.brz_customers")


@dp.table(name="slv_customers_lab7_quarantine")
def slv_customers_lab7_quarantine():
    return (
        spark.read.table("lab5.bronze.brz_customers")
        .transform(_customer_failure_reason)
        .filter("failure_reason IS NOT NULL AND failure_reason != ''")
    )


@dp.table(name="slv_sales_orders_lab7_valid")
@dp.expect_or_drop(
    "valid_lab7_order_record",
    "order_number IS NOT NULL AND customer_id IS NOT NULL AND CAST(number_of_line_items AS INT) > 0 AND order_datetime IS NOT NULL"
)
def slv_sales_orders_lab7_valid():
    return spark.read.table("lab5.bronze.brz_sales_orders")


@dp.table(name="slv_sales_orders_lab7_quarantine")
def slv_sales_orders_lab7_quarantine():
    return (
        spark.read.table("lab5.bronze.brz_sales_orders")
        .transform(_order_failure_reason)
        .filter("failure_reason IS NOT NULL AND failure_reason != ''")
    )
