from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window


# ---------- Customers: streaming bronze -> streaming silver ----------

@dp.table(
    name="slv_customers_clean",
    comment="Cleaned customer records. Types are converted and duplicate customer versions are removed."
)
@dp.expect_or_drop(
    "valid_customer_record",
    "customer_id IS NOT NULL AND valid_from_ts IS NOT NULL"
)
def slv_customers_clean():
    return (
        spark.readStream.table(
            f"{spark.conf.get('catalog')}.{spark.conf.get('bronze_schema')}.brz_customers"
        )
        .select(
            F.trim("customer_id").alias("customer_id"),
            F.trim("tax_id").alias("tax_id"),
            F.upper(F.trim("tax_code")).alias("tax_code"),
            F.initcap(F.trim("customer_name")).alias("customer_name"),
            F.upper(F.trim("state")).alias("state"),
            F.initcap(F.trim("city")).alias("city"),
            F.trim("postcode").alias("postcode"),
            F.initcap(F.trim("street")).alias("street"),
            F.trim("number").alias("street_number"),
            F.trim("unit").alias("unit"),
            F.upper(F.trim("region")).alias("region"),
            F.initcap(F.trim("district")).alias("district"),
            F.col("lon").cast("double").alias("longitude"),
            F.col("lat").cast("double").alias("latitude"),
            F.trim("ship_to_address").alias("ship_to_address"),
            F.to_timestamp(
                F.from_unixtime(F.col("valid_from").cast("bigint"))
            ).alias("valid_from_ts"),
            F.to_timestamp(
                F.from_unixtime(F.col("valid_to").cast("bigint"))
            ).alias("valid_to_ts"),
            F.col("units_purchased").cast("int").alias("units_purchased"),
            F.col("loyalty_segment").cast("int").alias("loyalty_segment"),
            F.col("_rescued_data"),
            F.col("source"),
            F.col("ingestion_timestamp"),
        )
        .withWatermark("valid_from_ts", "30 days")
        .dropDuplicates(["customer_id", "valid_from_ts"])
    )


# ---------- Orders: bronze batch snapshot -> silver batch materialized view ----------

@dp.materialized_view(
    name="slv_sales_orders_clean",
    comment="Cleaned sales orders with typed fields and one latest record per order number."
)
@dp.expect_or_drop(
    "valid_order",
    """
    order_number IS NOT NULL
    AND customer_id IS NOT NULL
    AND line_items > 0
    AND order_ts IS NOT NULL
    """
)
def slv_sales_orders_clean():
    orders = (
        spark.read.table(
        f"{spark.conf.get('catalog')}.{spark.conf.get('bronze_schema')}.brz_sales_orders"
        )
        .select(
            F.col("order_number"),
            F.trim("customer_id").alias("customer_id"),
            F.initcap(F.trim("customer_name")).alias("customer_name"),
            F.col("number_of_line_items").cast("int").alias("line_items"),
            F.to_timestamp(
                F.from_unixtime(F.col("order_datetime").cast("bigint"))
            ).alias("order_ts"),
            F.col("clicked_items"),
            F.col("ordered_products"),
            F.col("promo_info"),
            F.col("source"),
            F.col("ingestion_timestamp"),
        )
    )

    latest_order = Window.partitionBy("order_number").orderBy(
        F.col("order_ts").desc(),
        F.col("ingestion_timestamp").desc()
    )

    return (
        orders
        .withColumn("row_num", F.row_number().over(latest_order))
        .filter("row_num = 1")
        .drop("row_num")
    )


# ---------- Customers: SCD Type 2 history, managed declaratively ----------

dp.create_streaming_table(name="slv_customers_history")

dp.create_auto_cdc_flow(
    target="slv_customers_history",
    source="slv_customers_clean",
    keys=["customer_id"],
    sequence_by="valid_from_ts",
    stored_as_scd_type=2,
    except_column_list=[
        "valid_from_ts",
        "valid_to_ts",
        "source",
        "ingestion_timestamp",
        "_rescued_data",
    ],
    track_history_column_list=[
        "tax_id",
        "tax_code",
        "customer_name",
        "state",
        "city",
        "postcode",
        "street",
        "street_number",
        "unit",
        "region",
        "district",
        "longitude",
        "latitude",
        "ship_to_address",
        "units_purchased",
        "loyalty_segment",
    ],
)