-- Lab 10B: Delta Change Data Feed in the Academy workspace.
-- Writes only the Lab 10 source and target tables in the user's Bronze/Silver
-- schemas. Re-running the setup resets their data and CDF history.

-- Create an empty Delta source with CDF enabled before its first data change.
CREATE OR REPLACE TABLE
  dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc (
    customer_id INT,
    customer_name STRING,
    country STRING,
    segment STRING
  )
USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true);

SHOW TBLPROPERTIES
  dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc
  ('delta.enableChangeDataFeed');

-- Seed the initial five customers from the verified PostgreSQL foreign table.
INSERT INTO dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc
SELECT customer_id, customer_name, country, segment
FROM lab10_postgres_catalog.public.customers;

-- Initialize the current-state target from the initial source snapshot.
CREATE OR REPLACE TABLE
  dbr_dev.ayyuborujzade_silver.lab10_customers_target
AS
SELECT customer_id, customer_name, country, segment
FROM dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc;

-- Simulate one insert, one update, and one delete.
INSERT INTO dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc
VALUES (6, 'John Miller', 'Spain', 'Consumer');

UPDATE dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc
SET segment = 'Consumer'
WHERE customer_id = 2;

DELETE FROM dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc
WHERE customer_id = 5;

-- Inspect CDF events and their Delta commit metadata.
SELECT
  customer_id,
  customer_name,
  country,
  segment,
  _change_type,
  _commit_version,
  _commit_timestamp
FROM table_changes(
  'dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc',
  0
)
ORDER BY _commit_version, customer_id, _change_type;

-- Apply the latest insert, update postimage, or delete per customer.
-- Update preimages are excluded; the source CDF includes its five seed inserts.
MERGE INTO dbr_dev.ayyuborujzade_silver.lab10_customers_target AS target
USING (
  SELECT customer_id, customer_name, country, segment, _change_type
  FROM table_changes(
    'dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc',
    0
  )
  WHERE _change_type IN ('insert', 'update_postimage', 'delete')
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id
    ORDER BY _commit_version DESC
  ) = 1
) AS changes
ON target.customer_id = changes.customer_id
WHEN MATCHED AND changes._change_type = 'delete' THEN DELETE
WHEN MATCHED THEN UPDATE SET
  target.customer_name = changes.customer_name,
  target.country = changes.country,
  target.segment = changes.segment
WHEN NOT MATCHED AND changes._change_type <> 'delete' THEN INSERT (
  customer_id, customer_name, country, segment
) VALUES (
  changes.customer_id, changes.customer_name, changes.country, changes.segment
);

-- Expected final rows: customers 1, 2, 3, 4, and 6.
SELECT customer_id, customer_name, country, segment
FROM dbr_dev.ayyuborujzade_silver.lab10_customers_target
ORDER BY customer_id;

SELECT COUNT(*) AS customer_5_rows
FROM dbr_dev.ayyuborujzade_silver.lab10_customers_target
WHERE customer_id = 5;

SELECT COUNT(*) AS customer_6_rows
FROM dbr_dev.ayyuborujzade_silver.lab10_customers_target
WHERE customer_id = 6;

-- A zero count verifies source and target match in both directions.
SELECT COUNT(*) AS mismatched_rows
FROM (
  SELECT customer_id, customer_name, country, segment
  FROM dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc
  EXCEPT
  SELECT customer_id, customer_name, country, segment
  FROM dbr_dev.ayyuborujzade_silver.lab10_customers_target
  UNION ALL
  SELECT customer_id, customer_name, country, segment
  FROM dbr_dev.ayyuborujzade_silver.lab10_customers_target
  EXCEPT
  SELECT customer_id, customer_name, country, segment
  FROM dbr_dev.ayyuborujzade_bronze.lab10_customers_cdc
) AS differences;
