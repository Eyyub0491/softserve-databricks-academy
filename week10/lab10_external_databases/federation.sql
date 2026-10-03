-- Lab 10A: Lakehouse Federation with the validated Neon PostgreSQL source.
-- The connection and foreign catalog are assumed to have been configured
-- separately in the workspace. No connection credentials belong in this file.

-- Inspect rows in the foreign PostgreSQL tables.
SELECT *
FROM lab10_postgres_catalog.public.customers
LIMIT 20;

SELECT *
FROM lab10_postgres_catalog.public.orders
LIMIT 20;

-- Compare the customer count in PostgreSQL with the replicated Delta copy.
SELECT COUNT(*) AS federation_customer_count
FROM lab10_postgres_catalog.public.customers;

-- Materialize a Delta copy of the foreign customers table.
CREATE TABLE IF NOT EXISTS workspace.default.lab10_customers_delta
AS
SELECT *
FROM lab10_postgres_catalog.public.customers;

SELECT COUNT(*) AS delta_customer_count
FROM workspace.default.lab10_customers_delta;

-- Join live foreign data to the Delta copy on the customer key.
-- Select the columns required by the exercise if the source has other columns.
SELECT
  p.customer_id,
  p.customer_name,
  p.country,
  p.segment,
  d.customer_name AS delta_customer_name
FROM lab10_postgres_catalog.public.customers AS p
INNER JOIN workspace.default.lab10_customers_delta AS d
  ON p.customer_id = d.customer_id
ORDER BY p.customer_id;

-- Validation observed in the Free/DEV workspace: both counts were 5.
