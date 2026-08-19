from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("catalog")
BRONZE_SCHEMA = spark.conf.get("bronze_schema")

@dp.table(
    name="brz_customers"
)
@dp.expect_or_drop(
    "valid_customer_id",
    "customer_id IS NOT NULL"
)
def brz_customers():

    return (
        spark.readStream
        .format("cloudFiles") \
        .option("cloudFiles.format", "csv") \
        .option(
        "cloudFiles.schemaLocation",
        f"/Volumes/{CATALOG}/{BRONZE_SCHEMA}/checkpoints/customers_schema_landing_v1"
        ) \
        .option("header", "true") \
        .load(f"/Volumes/{CATALOG}/{BRONZE_SCHEMA}/customer_landing/")
        .withColumn(
        "source",
        F.lit(f"{CATALOG}/{BRONZE_SCHEMA}/customer_landing")
        )
        .withColumn("ingestion_timestamp", F.current_timestamp())
    )


@dp.materialized_view(
    name="brz_sales_orders"
)
def brz_sales_orders():

    return (
        spark.read
        .json("dbfs:/databricks-datasets/retail-org/sales_orders/")
        .withColumn("source", F.lit("retail-org/sales_orders"))
        .withColumn("ingestion_timestamp", F.current_timestamp())
    )