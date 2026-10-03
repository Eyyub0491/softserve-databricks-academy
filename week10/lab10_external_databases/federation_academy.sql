-- Academy-specific Lab 10A: Lakehouse Federation.
-- Target catalog: dbr_dev. All Delta output is isolated in this user's
-- existing Bronze schema. The external connection/catalog must already exist.

-- Read foreign PostgreSQL tables. These statements do not copy or modify them.
SELECT *
FROM lab10_postgres_catalog.public.customers
LIMIT 20;

SELECT *
FROM lab10_postgres_catalog.public.orders
LIMIT 20;

SELECT COUNT(*) AS federation_customer_count
FROM lab10_postgres_catalog.public.customers;

-- Create the Delta snapshot only if it does not already exist.
CREATE TABLE IF NOT EXISTS
  dbr_dev.ayyuborujzade_bronze.lab10_customers_delta
AS
SELECT *
FROM lab10_postgres_catalog.public.customers;

SELECT COUNT(*) AS delta_customer_count
FROM dbr_dev.ayyuborujzade_bronze.lab10_customers_delta;

-- Join live foreign data to the Delta snapshot using the customer key.
SELECT
  p.customer_id,
  p.customer_name,
  p.country,
  p.segment,
  d.customer_name AS delta_customer_name
FROM lab10_postgres_catalog.public.customers AS p
INNER JOIN dbr_dev.ayyuborujzade_bronze.lab10_customers_delta AS d
  ON p.customer_id = d.customer_id
ORDER BY p.customer_id;

-- The validated Free/DEV run returned 5 customers from each source.
