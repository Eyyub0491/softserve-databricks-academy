# Lab 4 - Silver Layer, Data Quality & Schema Evolution

Builds a governed Silver layer on top of Databricks' `retail-org` sample dataset (customers +
sales orders), covering deduplication, SCD Type 1/2, schema enforcement & evolution, a
lightweight data-quality quarantine pattern, and table maintenance.

## Notebooks

| # | Notebook | What it does |
|---|----------|---------------|
| 01 | `01_bronze_ingestion` | Loads raw customers (CSV) and sales orders (nested JSON) into `bronze` as **raw strings**, with `source`/`ingestion_timestamp` metadata. Rerunnable via `overwrite`. |
| 02 | `02_silver_customers` | Casts bronze strings to proper types, quarantines rows that fail the merge-key cast, dedupes, and builds an **SCD Type 2** table (full change history via `effective_start`/`effective_end`/`is_current`). |
| 03 | `03_silver_sales_orders` | Flattens the nested `ordered_products` array into one row per line item, casts every numeric field, quarantines rows with a broken merge key, dedupes, and builds an **SCD Type 1** fact table (corrections just overwrite, no history). |
| 04 | `04_schema_enforcement_evolution` | Proves Delta rejects a mismatched-schema write by default, then shows the controlled way past it (`mergeSchema`), column widening, Delta column mapping (safe rename/drop), and a simple data-contract check. |
| 05 | `05_table_maintenance` | `OPTIMIZE`, `VACUUM`, and Liquid Clustering on the Silver tables, with a discussion of the trade-offs vs. `ZORDER` and classic partitioning. |

## Design decisions

**Bronze = raw strings, Silver = typed + deduped.** Bronze ingestion doesn't infer types or
clean anything — every column lands as `STRING`, exactly as the source produced it. All
casting, validation, and deduplication happens in Silver. This keeps bronze immune to a load
failing because of one malformed value, and keeps the "what did the source actually send"
history intact.

**Data quality via quarantine, not silent nulls.** Casts use `try_cast`, which returns `null`
instead of failing the job on bad input. For non-key columns that's fine — but for merge-key
columns (`customer_id`, or `order_number`/`product_id`), a row that fails to cast doesn't get
merged as if it were valid. It's routed instead to a dedicated quarantine table
(`slv_customers_quarantine`, `slv_sales_order_lines_quarantine`) with the original raw value
and a rejection reason, so bad data is visible and inspectable rather than silently dropped.

**SCD Type 1 vs Type 2, matched to the data's nature.** Customers is a slowly-changing
dimension — history matters, so it's Type 2. Sales orders is a fact table — a correction should
just replace the old value, not spawn a history row, so it's Type 1.

**Schema evolution is opt-in, not automatic.** `mergeSchema` is never left on by default; it's
applied deliberately when a specific, expected schema change happens. A lightweight data
contract check (in `04`) makes structural drift fail loudly rather than pass silently.

## Running

Each notebook takes a `catalog` widget (default `lab4`). Run in order, `01` → `05` — each
Silver notebook depends on its bronze table already existing, and `04`/`05` depend on
`03` having created `slv_sales_order_lines`.
