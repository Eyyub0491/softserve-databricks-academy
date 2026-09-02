# Lab 7 - Testing & Data Quality

## Overview

This lab adds a local test and data-quality layer around the existing Lab 5 and Lab 6 work. It covers unit tests for transformation logic, DQ checks, Databricks integration tests, DQX validation, and a Lakeflow expectations layer based on the real Bronze source tables.

The project keeps the production Lab 5 and Lab 6 pipelines untouched and validates the existing data quality around them.

## Project structure

```text
lab7_testing_dq/
├── dq/
├── lakeflow/
├── src/
├── tests/
│   ├── integration/
│   └── unit/
├── conftest.py
├── databricks.yml
├── pytest.ini
├── README.md
├── requirements.txt
└── .gitignore
```

## Unit tests

The unit tests focus on business behavior rather than only checking schemas or row counts. They cover things like:

- string normalization
- date conversion
- loyalty segment mapping
- validation rules
- business calculations

Run the unit suite with:

```bash
cd week07/lab7_testing_dq
../.venv-connect/Scripts/python.exe -m pytest tests/unit -q
```

## Data quality and DQX

The DQ checks in `dq/` validate things such as:

- completeness of required fields
- uniqueness of keys
- range validation
- referential integrity checks
- reconciliation checks

The DQX checks in `dq/dqx_checks.py` validate the real workspace data with the official Databricks Labs DQX library. They currently cover:

- customer completeness and range validation
- duplicate customer IDs
- fact-to-dimension integrity for customer, product, and date keys

Run the DQX integration tests with:

```bash
cd week07/lab7_testing_dq
DATABRICKS_RUN_INTEGRATION=1 DATABRICKS_CLUSTER_ID=<cluster-id> DATABRICKS_PROFILE=DEFAULT ../.venv-connect/Scripts/python.exe -m pytest tests/integration/test_dqx_checks.py -q
```

## Lakeflow expectations

Lab 7 adds a separate Lakeflow validation layer on top of the existing Bronze source tables from Lab 5:

```text
lab5.bronze.brz_customers
lab5.bronze.brz_sales_orders
```

The implemented customer expectations are:

- `customer_id IS NOT NULL`
- `state IS NOT NULL`
- `city IS NOT NULL`
- `valid_from IS NOT NULL`
- `loyalty_segment BETWEEN 0 AND 3`
- `units_purchased >= 0`

The implemented order expectations are:

- `order_number IS NOT NULL`
- `customer_id IS NOT NULL`
- `number_of_line_items > 0`
- `order_datetime IS NOT NULL`

The valid output tables are:

```text
lab5.silver.slv_customers_lab7_valid
lab5.silver.slv_sales_orders_lab7_valid
```

## Quarantine

The Lab 7 Lakeflow project keeps quarantine as an explicit branch from the Bronze source. This is separate from `expect_or_drop` and retains invalid rows instead of silently dropping them. The quarantine outputs are:

```text
lab5.silver.slv_customers_lab7_quarantine
lab5.silver.slv_sales_orders_lab7_quarantine
```

Each quarantine row keeps the original fields and adds a `failure_reason` column describing which rule or rules failed.

## Integration tests

The integration tests use Databricks Connect/serverless and validate the deployed Lakeflow outputs against the source Bronze tables.

They check that:

- valid + quarantine rows cover the source rows
- valid rows satisfy the expected rules
- quarantine rows violate at least one rule
- quarantine rows include a non-empty `failure_reason`

The freshness rule is tested deterministically in the unit suite with controlled timestamps. The Academy Bronze tables are a static lab snapshot, so integration tests check that inherited `ingestion_timestamp` provenance exists rather than applying a live freshness SLA to it.

Run the Lakeflow integration checks with:

```bash
cd week07/lab7_testing_dq
DATABRICKS_RUN_INTEGRATION=1 DATABRICKS_CLUSTER_ID=<cluster-id> DATABRICKS_PROFILE=DEFAULT ../.venv-connect/Scripts/python.exe -m pytest tests/integration/test_lab7_lakeflow_outputs.py -q
```

## Local validation

```bash
cd week07/lab7_testing_dq
../.venv-connect/Scripts/python.exe -m pytest tests/unit -q
../.venv-connect/Scripts/python.exe -m compileall lakeflow tests dq src
databricks bundle validate --profile DEFAULT
```

## Deployment

The project includes a Databricks bundle definition in `databricks.yml`.

Deploy with:

```bash
databricks bundle deploy --target dev --profile DEFAULT
```

Run the integration checks after the Lakeflow pipeline has been deployed and executed.

Lab 5 and Lab 6 production pipelines are unchanged. Credentials and tokens are not stored in the repository.
