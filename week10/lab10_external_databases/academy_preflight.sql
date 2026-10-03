-- Read-only Academy preflight. Stop if identity/catalog/foreign-source checks
-- do not match expectations. No resource is created or changed by this file.

SELECT
  current_user() AS authenticated_user,
  current_catalog() AS current_catalog,
  current_schema() AS current_schema;

SHOW CATALOGS LIKE 'lab10_postgres_catalog';
SHOW SCHEMAS IN lab10_postgres_catalog LIKE 'public';
SHOW TABLES IN lab10_postgres_catalog.public LIKE 'customers';
SHOW TABLES IN lab10_postgres_catalog.public LIKE 'orders';

-- This query confirms read access to the PostgreSQL foreign table.
SELECT COUNT(*) AS foreign_customer_count
FROM lab10_postgres_catalog.public.customers;

-- Report any same-named Lab 10 tables before considering the write scripts.
SHOW TABLES IN dbr_dev.ayyuborujzade_bronze LIKE 'lab10_customers_delta';
SHOW TABLES IN dbr_dev.ayyuborujzade_bronze LIKE 'lab10_customers_cdc';
SHOW TABLES IN dbr_dev.ayyuborujzade_silver LIKE 'lab10_customers_target';
