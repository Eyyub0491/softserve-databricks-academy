# Lab 5 — Lakeflow Declarative Pipelines

## Overview

This project is my SoftServe Academy Lab 5 solution using Databricks Lakeflow Spark Declarative Pipelines.

It demonstrates:

- Streaming CSV ingestion with Auto Loader
- Batch ingestion of nested JSON
- Bronze and silver layers
- Data-quality expectations
- Unity Catalog lineage
- Safe incremental reloads
- SCD Type 2 customer history with `create_auto_cdc_flow()`
- Asset Bundle deployment preparation

## Architecture

```text
Customer CSV files in Unity Catalog Volume
        │
        ▼
lab5.bronze.brz_customers
        │
        ▼
lab5.silver.slv_customers_clean
        │
        ▼
lab5.silver.slv_customers_history
(SCD Type 2)

Nested sales-orders JSON files
        │
        ▼
lab5.bronze.brz_sales_orders
        │
        ▼
lab5.silver.slv_sales_orders_clean
```

## Project structure

```text
declarative_pipelines/
├── lab5_bronze/
│   └── transformations/
│       └── bronze_pipeline.py
├── lab5_silver/
│   └── transformations/
│       └── silver_pipeline.py
├── setup/
│   ├── 00_create_lab5_objects.sql
│   └── 01_seed_customer_landing
├── validation/
│   └── 02_lab5_validation_queries
├── docs/
│   └── screenshots/
└── README.md
```

## Databricks objects

```sql
CREATE CATALOG IF NOT EXISTS lab5;

CREATE SCHEMA IF NOT EXISTS lab5.bronze;
CREATE SCHEMA IF NOT EXISTS lab5.silver;

CREATE VOLUME IF NOT EXISTS lab5.bronze.checkpoints;
CREATE VOLUME IF NOT EXISTS lab5.bronze.customer_landing;
```

`customer_landing` is a writable Unity Catalog Volume used to test incremental Auto Loader ingestion and SCD Type 2 changes.

## Bronze pipeline

| Dataset | Type | Source |
|---|---|---|
| `lab5.bronze.brz_customers` | Streaming table | CSV files in `customer_landing` Volume |
| `lab5.bronze.brz_sales_orders` | Materialized view | Nested sales-orders JSON |

Customer data is loaded incrementally using Auto Loader:

```python
spark.readStream \
    .format("cloudFiles") \
    .option("cloudFiles.format", "csv") \
    .option(
        "cloudFiles.schemaLocation",
        "/Volumes/lab5/bronze/checkpoints/customers_schema_landing_v1"
    ) \
    .option("header", "true") \
    .load("/Volumes/lab5/bronze/customer_landing/")
```

Bronze expectation:

```python
@dp.expect_or_drop(
    "valid_customer_id",
    "customer_id IS NOT NULL"
)
```

## Silver pipeline

| Dataset | Type | Purpose |
|---|---|---|
| `lab5.silver.slv_customers_clean` | Streaming table | Cleaned, typed, and deduplicated customers |
| `lab5.silver.slv_sales_orders_clean` | Materialized view | Cleaned and deduplicated sales orders |
| `lab5.silver.slv_customers_history` | Streaming table | Customer SCD Type 2 history |

Customer transformations include text standardization, type conversions, Unix timestamp conversion, watermarking, and streaming-safe deduplication.

Customer expectation:

```python
@dp.expect_or_drop(
    "valid_customer_record",
    "customer_id IS NOT NULL AND valid_from_ts IS NOT NULL"
)
```

Sales-order transformations include converting line-item counts and timestamps, plus retaining the latest record for each `order_number`.

Sales-order expectation:

```python
@dp.expect_or_drop(
    "valid_order",
    """
    order_number IS NOT NULL
    AND customer_id IS NOT NULL
    AND line_items > 0
    AND order_ts IS NOT NULL
    """
)
```

## SCD Type 2 demonstration

Customer history is handled declaratively:

```python
dp.create_auto_cdc_flow(
    target="slv_customers_history",
    source="slv_customers_clean",
    keys=["customer_id"],
    sequence_by="valid_from_ts",
    stored_as_scd_type=2,
    ...
)
```

A synthetic customer was added to prove SCD Type 2 behavior:

```sql
SELECT
  customer_id,
  city,
  loyalty_segment,
  __START_AT,
  __END_AT
FROM lab5.silver.slv_customers_history
WHERE customer_id = 'SCD_DEMO_001'
ORDER BY __START_AT;
```

Result:

```text
SCD_DEMO_001 | Seattle | 1 | 2024-01-01 | 2024-04-01
SCD_DEMO_001 | Tacoma  | 2 | 2024-04-01 | null
```

The old Seattle version was closed, and Tacoma became the active customer version.

## Safe reload

Auto Loader manages processed-file state through its schema/checkpoint location.

Normal pipeline updates process only new files. After adding the second synthetic customer version, both pipelines were updated normally without a Full refresh.

A Full refresh was used only once when the Auto Loader input moved from the shared sample path to the Unity Catalog Volume.

Validation queries:

```sql
SELECT COUNT(*) AS customer_history_rows
FROM lab5.silver.slv_customers_history;

SELECT COUNT(*) AS clean_order_rows
FROM lab5.silver.slv_sales_orders_clean;
```

When no new files are added, normal updates should leave these counts unchanged.

## Data lineage

Unity Catalog lineage shows:

```text
brz_customers
→ slv_customers_clean
→ slv_customers_history
```

```text
brz_sales_orders
→ slv_sales_orders_clean
```

## Declarative Pipelines vs classic Spark jobs

| Topic | Classic Spark job | Lakeflow Declarative Pipeline |
|---|---|---|
| Development model | Imperative code | Declarative dataset definitions |
| Dependencies | Managed manually | Dependency graph generated automatically |
| Data quality | Custom validation code | Expectations declared with datasets |
| Streaming state | Manual checkpoints and state handling | Managed state and Auto Loader tracking |
| SCD Type 2 | Usually custom `MERGE` logic | `create_auto_cdc_flow()` |
| Flexibility | Highest low-level control | Simpler standard ETL and streaming patterns |
| Operations | More engineering effort | Built-in quality metrics and lineage |

Lakeflow Declarative Pipelines simplify reliable batch and streaming ETL by managing dependencies, data quality, lineage, incremental state, and SCD processing. Classic Spark jobs remain useful for highly customized workloads requiring fine-grained control.

## Evidence

Screenshots will be saved in `docs/screenshots/`:

```text
01_bronze_pipeline_graph.png
02_silver_pipeline_graph.png
03_bronze_expectation.png
04_silver_customer_expectation.png
05_silver_order_expectation.png
06_customer_lineage.png
07_orders_lineage.png
08_scd2_proof.png
09_safe_incremental_reload.png
```

No screenshots include real customer names, addresses, or other PII-like data.

## Asset Bundle deployment

The final deployment will use a Databricks Asset Bundle containing:

- Bronze and silver pipeline source code
- Schema and Volume resources
- Pipeline resource definitions
- One-time setup script