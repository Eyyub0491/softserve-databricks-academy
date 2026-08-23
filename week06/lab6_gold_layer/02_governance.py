# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 6 - Governance
# MAGIC
# MAGIC Implements Unity Catalog governance controls: permissions, row-level security, and column masking.
# MAGIC
# MAGIC ## Permissions
# MAGIC
# MAGIC Grants the `account users` group access to the Gold schema.
# MAGIC
# MAGIC **Note:** The GRANT statements below document the required permissions. These have already been applied to the workspace.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- GRANT USE SCHEMA ON SCHEMA lab5.gold TO `account users`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- GRANT SELECT ON SCHEMA lab5.gold TO `account users`;

# COMMAND ----------

# MAGIC %sql
# MAGIC SHOW GRANTS ON SCHEMA lab5.gold;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Row-Level Security
# MAGIC
# MAGIC Restricts dim_customers to show only CA, NY, and TX states.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION lab5.gold.filter_customers_by_state(state STRING)
# MAGIC RETURNS BOOLEAN
# MAGIC RETURN state IN ('CA', 'NY', 'TX');

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE lab5.gold.dim_customers
# MAGIC SET ROW FILTER lab5.gold.filter_customers_by_state ON (state);

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     state,
# MAGIC     COUNT(*) AS customer_count
# MAGIC FROM lab5.gold.dim_customers
# MAGIC GROUP BY state
# MAGIC ORDER BY state;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Column-Level Security
# MAGIC
# MAGIC Masks tax_id for non-admin users.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION lab5.gold.mask_tax_id(value STRING)
# MAGIC RETURN CASE
# MAGIC     WHEN is_account_group_member('admins') THEN value
# MAGIC     ELSE 'REDACTED'
# MAGIC END;

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE lab5.gold.dim_customers
# MAGIC ALTER COLUMN tax_id
# MAGIC SET MASK lab5.gold.mask_tax_id;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     customer_id,
# MAGIC     customer_name,
# MAGIC     tax_id
# MAGIC FROM lab5.gold.dim_customers
# MAGIC WHERE tax_id IS NOT NULL
# MAGIC LIMIT 10;