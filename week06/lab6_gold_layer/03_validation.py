# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 6 - Validation
# MAGIC
# MAGIC Final checks for the Gold layer tables and governance controls.
# MAGIC
# MAGIC ## Gold Layer Checks
# MAGIC
# MAGIC Verifies row counts, data quality, and referential integrity.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'dim_date' as table_name, COUNT(*) as row_count 
# MAGIC FROM lab5.gold.dim_date
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 'dim_customers', COUNT(*) 
# MAGIC FROM lab5.gold.dim_customers
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 'dim_products', COUNT(*) 
# MAGIC FROM lab5.gold.dim_products;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   COUNT(*) as total_rows,
# MAGIC   COUNT(DISTINCT order_line_key) as unique_keys,
# MAGIC   COUNT(DISTINCT order_number) as distinct_orders,
# MAGIC   COUNT(DISTINCT customer_key) as distinct_customers,
# MAGIC   COUNT(DISTINCT product_key) as distinct_products,
# MAGIC   COUNT(customer_key) as non_null_customer_keys,
# MAGIC   COUNT(product_key) as non_null_product_keys,
# MAGIC   COUNT(date_key) as non_null_date_keys
# MAGIC FROM lab5.gold.fct_sales_orders;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   'fct_sales_orders' as source, 
# MAGIC   COUNT(DISTINCT order_number) as orders, 
# MAGIC   ROUND(SUM(line_total), 2) as revenue
# MAGIC FROM lab5.gold.fct_sales_orders
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'agg_customer_summary', 
# MAGIC   SUM(total_orders), 
# MAGIC   ROUND(SUM(total_revenue), 2)
# MAGIC FROM lab5.gold.agg_customer_summary
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'agg_daily_sales', 
# MAGIC   SUM(total_orders), 
# MAGIC   ROUND(SUM(total_revenue), 2)
# MAGIC FROM lab5.gold.agg_daily_sales;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Governance Validation
# MAGIC
# MAGIC Verifies RLS and CLS are working correctly.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     state,
# MAGIC     COUNT(*) AS customer_count
# MAGIC FROM lab5.gold.dim_customers
# MAGIC GROUP BY state
# MAGIC ORDER BY state;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     customer_id,
# MAGIC     customer_name,
# MAGIC     tax_id
# MAGIC FROM lab5.gold.dim_customers
# MAGIC WHERE tax_id IS NOT NULL
# MAGIC LIMIT 10;