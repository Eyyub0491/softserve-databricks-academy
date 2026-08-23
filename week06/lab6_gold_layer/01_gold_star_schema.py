# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 6 - Gold Star Schema
# MAGIC
# MAGIC Creates the Gold layer tables used for analytics.
# MAGIC
# MAGIC ## Star Schema
# MAGIC - **Dimensions**: dim_date, dim_customers, dim_products
# MAGIC - **Fact**: fct_sales_orders (order line items, one row per product ordered)
# MAGIC - **Aggregations**: agg_customer_summary (customer lifetime value), agg_daily_sales (daily metrics for alerting)
# MAGIC
# MAGIC ## Source Data
# MAGIC - lab5.silver.slv_sales_orders_clean
# MAGIC - lab5.silver.slv_customers_clean

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE lab5.gold.dim_date
# MAGIC COMMENT 'Date dimension table covering sales order period (July-Dec 2019) with standard calendar attributes'
# MAGIC AS
# MAGIC WITH date_spine AS (
# MAGIC   SELECT 
# MAGIC     EXPLODE(
# MAGIC       SEQUENCE(
# MAGIC         TO_DATE('2019-07-01'), 
# MAGIC         TO_DATE('2019-12-31'), 
# MAGIC         INTERVAL 1 DAY
# MAGIC       )
# MAGIC     ) AS full_date
# MAGIC )
# MAGIC SELECT 
# MAGIC   CAST(DATE_FORMAT(full_date, 'yyyyMMdd') AS INT) AS date_key,
# MAGIC   
# MAGIC   full_date,
# MAGIC   
# MAGIC   YEAR(full_date) AS year,
# MAGIC   QUARTER(full_date) AS quarter,
# MAGIC   MONTH(full_date) AS month,
# MAGIC   DATE_FORMAT(full_date, 'MMMM') AS month_name,
# MAGIC   
# MAGIC   WEEKOFYEAR(full_date) AS week_of_year,
# MAGIC   DAYOFMONTH(full_date) AS day_of_month,
# MAGIC   DAYOFWEEK(full_date) AS day_of_week,
# MAGIC   DATE_FORMAT(full_date, 'EEEE') AS day_name,
# MAGIC   
# MAGIC   CASE WHEN DAYOFWEEK(full_date) IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekend
# MAGIC   
# MAGIC FROM date_spine
# MAGIC ORDER BY full_date;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   'Total rows' AS metric,
# MAGIC   CAST(COUNT(*) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_date
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Min date' AS metric,
# MAGIC   CAST(MIN(full_date) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_date
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Max date' AS metric,
# MAGIC   CAST(MAX(full_date) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_date
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Min date_key' AS metric,
# MAGIC   CAST(MIN(date_key) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_date
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Max date_key' AS metric,
# MAGIC   CAST(MAX(date_key) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_date
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Weekday days' AS metric,
# MAGIC   CAST(COUNT(*) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_date
# MAGIC WHERE is_weekend = FALSE
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Weekend days' AS metric,
# MAGIC   CAST(COUNT(*) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_date
# MAGIC WHERE is_weekend = TRUE;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE lab5.gold.dim_customers
# MAGIC COMMENT 'Current customer dimension with demographics, loyalty status, and order flags for Lab 6 Gold analytics'
# MAGIC AS
# MAGIC WITH current_customers AS (
# MAGIC   SELECT 
# MAGIC     customer_id,
# MAGIC     customer_name,
# MAGIC     tax_id,
# MAGIC     tax_code,
# MAGIC     state,
# MAGIC     city,
# MAGIC     region,
# MAGIC     postcode,
# MAGIC     loyalty_segment,
# MAGIC     units_purchased,
# MAGIC     valid_from_ts,
# MAGIC     ROW_NUMBER() OVER (
# MAGIC       PARTITION BY customer_id 
# MAGIC       ORDER BY valid_from_ts DESC
# MAGIC     ) AS rn
# MAGIC   FROM lab5.silver.slv_customers_clean
# MAGIC   WHERE valid_to_ts IS NULL
# MAGIC ),
# MAGIC customers_with_orders AS (
# MAGIC   SELECT DISTINCT customer_id
# MAGIC   FROM lab5.silver.slv_sales_orders_clean
# MAGIC )
# MAGIC SELECT 
# MAGIC   ABS(HASH(c.customer_id)) AS customer_key,
# MAGIC   
# MAGIC   c.customer_id,
# MAGIC   
# MAGIC   c.customer_name,
# MAGIC   c.tax_id,
# MAGIC   c.tax_code,
# MAGIC   c.state,
# MAGIC   c.city,
# MAGIC   c.region,
# MAGIC   c.postcode,
# MAGIC   
# MAGIC   c.loyalty_segment,
# MAGIC   CASE c.loyalty_segment
# MAGIC     WHEN 0 THEN 'None'
# MAGIC     WHEN 1 THEN 'Bronze'
# MAGIC     WHEN 2 THEN 'Silver'
# MAGIC     WHEN 3 THEN 'Gold'
# MAGIC     ELSE 'Unknown'
# MAGIC   END AS loyalty_segment_name,
# MAGIC   
# MAGIC   c.units_purchased,
# MAGIC   
# MAGIC   CASE 
# MAGIC     WHEN o.customer_id IS NOT NULL THEN TRUE 
# MAGIC     ELSE FALSE 
# MAGIC   END AS has_orders,
# MAGIC   
# MAGIC   DATE(c.valid_from_ts) AS effective_date,
# MAGIC   
# MAGIC   TRUE AS is_current
# MAGIC   
# MAGIC FROM current_customers c
# MAGIC LEFT JOIN customers_with_orders o 
# MAGIC   ON c.customer_id = o.customer_id
# MAGIC WHERE c.rn = 1
# MAGIC ORDER BY c.customer_id;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   'Total rows' AS metric,
# MAGIC   CAST(COUNT(*) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_customers
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Unique customer_id' AS metric,
# MAGIC   CAST(COUNT(DISTINCT customer_id) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_customers
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Unique customer_key' AS metric,
# MAGIC   CAST(COUNT(DISTINCT customer_key) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_customers;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE lab5.gold.dim_products
# MAGIC COMMENT 'Product dimension with ordering history for Lab 6 Gold analytics'
# MAGIC AS
# MAGIC WITH exploded_products AS (
# MAGIC   SELECT 
# MAGIC     DATE(order_ts) as order_date,
# MAGIC     product.id as product_id,
# MAGIC     product.name as product_name
# MAGIC   FROM lab5.silver.slv_sales_orders_clean
# MAGIC   LATERAL VIEW EXPLODE(ordered_products) AS product
# MAGIC ),
# MAGIC product_aggregates AS (
# MAGIC   SELECT 
# MAGIC     product_id,
# MAGIC     product_name,
# MAGIC     MIN(order_date) as first_order_date,
# MAGIC     MAX(order_date) as last_order_date,
# MAGIC     COUNT(*) as times_ordered
# MAGIC   FROM exploded_products
# MAGIC   GROUP BY product_id, product_name
# MAGIC )
# MAGIC SELECT 
# MAGIC   ABS(HASH(product_id)) AS product_key,
# MAGIC   
# MAGIC   product_id,
# MAGIC   
# MAGIC   product_name,
# MAGIC   
# MAGIC   first_order_date,
# MAGIC   last_order_date,
# MAGIC   times_ordered
# MAGIC   
# MAGIC FROM product_aggregates
# MAGIC ORDER BY product_id;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   'Total rows' AS metric,
# MAGIC   CAST(COUNT(*) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_products
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Unique product_id' AS metric,
# MAGIC   CAST(COUNT(DISTINCT product_id) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_products
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Unique product_key' AS metric,
# MAGIC   CAST(COUNT(DISTINCT product_key) AS STRING) AS value
# MAGIC FROM lab5.gold.dim_products;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE lab5.gold.fct_sales_orders
# MAGIC COMMENT 'Sales order line items fact table with one row per product ordered'
# MAGIC AS
# MAGIC WITH exploded_orders AS (
# MAGIC   SELECT 
# MAGIC     o.order_number,
# MAGIC     o.customer_id,
# MAGIC     o.order_ts,
# MAGIC     product.id as product_id,
# MAGIC     product.name as product_name,
# MAGIC     product.price as price_cents,
# MAGIC     product.qty as quantity,
# MAGIC     product.curr as currency,
# MAGIC     product.unit as unit_of_measure,
# MAGIC     product.promotion_info.promo_disc as promo_disc_pct,
# MAGIC     product.promotion_info.promo_id as promo_id,
# MAGIC     ROW_NUMBER() OVER (PARTITION BY o.order_number ORDER BY product.id) as line_sequence
# MAGIC   FROM lab5.silver.slv_sales_orders_clean o
# MAGIC   LATERAL VIEW EXPLODE(o.ordered_products) AS product
# MAGIC )
# MAGIC SELECT 
# MAGIC   e.order_number * 1000 + e.line_sequence AS order_line_key,
# MAGIC   
# MAGIC   e.order_number,
# MAGIC   c.customer_key,
# MAGIC   p.product_key,
# MAGIC   d.date_key,
# MAGIC   
# MAGIC   e.order_ts,
# MAGIC   
# MAGIC   e.product_id,
# MAGIC   
# MAGIC   e.quantity,
# MAGIC   CAST(e.price_cents / 100.0 AS DECIMAL(10,2)) as unit_price,
# MAGIC   CAST((e.price_cents * e.quantity) / 100.0 AS DECIMAL(10,2)) as line_total,
# MAGIC   
# MAGIC   CAST(
# MAGIC     COALESCE(e.price_cents * e.quantity * e.promo_disc_pct, 0) / 100.0 
# MAGIC     AS DECIMAL(10,2)
# MAGIC   ) as promotion_discount,
# MAGIC   COALESCE(e.promo_id, 0) as promotion_id,
# MAGIC   CASE 
# MAGIC     WHEN e.promo_disc_pct IS NOT NULL AND e.promo_disc_pct > 0 
# MAGIC     THEN TRUE 
# MAGIC     ELSE FALSE 
# MAGIC   END as has_promotion,
# MAGIC   
# MAGIC   e.currency,
# MAGIC   e.unit_of_measure
# MAGIC   
# MAGIC FROM exploded_orders e
# MAGIC INNER JOIN lab5.gold.dim_customers c 
# MAGIC   ON e.customer_id = c.customer_id
# MAGIC INNER JOIN lab5.gold.dim_products p 
# MAGIC   ON e.product_id = p.product_id
# MAGIC INNER JOIN lab5.gold.dim_date d 
# MAGIC   ON DATE(e.order_ts) = d.full_date
# MAGIC ORDER BY e.order_number, e.line_sequence;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   'Total fact rows' AS metric,
# MAGIC   CAST(COUNT(*) AS STRING) AS value
# MAGIC FROM lab5.gold.fct_sales_orders
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Distinct order_line_key' AS metric,
# MAGIC   CAST(COUNT(DISTINCT order_line_key) AS STRING) AS value
# MAGIC FROM lab5.gold.fct_sales_orders
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Distinct orders' AS metric,
# MAGIC   CAST(COUNT(DISTINCT order_number) AS STRING) AS value
# MAGIC FROM lab5.gold.fct_sales_orders
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Distinct customers' AS metric,
# MAGIC   CAST(COUNT(DISTINCT customer_key) AS STRING) AS value
# MAGIC FROM lab5.gold.fct_sales_orders
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Distinct products' AS metric,
# MAGIC   CAST(COUNT(DISTINCT product_key) AS STRING) AS value
# MAGIC FROM lab5.gold.fct_sales_orders;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Aggregations
# MAGIC
# MAGIC Customer-level and daily-level aggregates for business reporting and alerting.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE lab5.gold.agg_customer_summary
# MAGIC COMMENT 'Customer-level sales summary with lifetime value metrics for customers who have placed orders'
# MAGIC AS
# MAGIC WITH customer_metrics AS (
# MAGIC   SELECT 
# MAGIC     f.customer_key,
# MAGIC     COUNT(DISTINCT f.order_number) as total_orders,
# MAGIC     COUNT(*) as total_line_items,
# MAGIC     SUM(f.quantity) as total_quantity,
# MAGIC     SUM(f.line_total) as total_revenue,
# MAGIC     MIN(DATE(f.order_ts)) as first_order_date,
# MAGIC     MAX(DATE(f.order_ts)) as last_order_date
# MAGIC   FROM lab5.gold.fct_sales_orders f
# MAGIC   GROUP BY f.customer_key
# MAGIC )
# MAGIC SELECT 
# MAGIC   cm.customer_key,
# MAGIC   c.customer_id,
# MAGIC   c.customer_name,
# MAGIC   c.state,
# MAGIC   c.loyalty_segment_name,
# MAGIC   
# MAGIC   cm.total_orders,
# MAGIC   cm.total_line_items,
# MAGIC   cm.total_quantity,
# MAGIC   CAST(cm.total_revenue AS DECIMAL(10,2)) as total_revenue,
# MAGIC   CAST(cm.total_revenue / cm.total_orders AS DECIMAL(10,2)) as avg_order_value,
# MAGIC   
# MAGIC   cm.first_order_date,
# MAGIC   cm.last_order_date,
# MAGIC   DATEDIFF(CURRENT_DATE(), cm.last_order_date) as days_since_last_order
# MAGIC   
# MAGIC FROM customer_metrics cm
# MAGIC INNER JOIN lab5.gold.dim_customers c 
# MAGIC   ON cm.customer_key = c.customer_key
# MAGIC ORDER BY cm.total_revenue DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE lab5.gold.agg_daily_sales
# MAGIC COMMENT 'Daily sales summary with order volume, revenue, and customer metrics for dashboard and alerting'
# MAGIC AS
# MAGIC WITH daily_metrics AS (
# MAGIC   SELECT 
# MAGIC     DATE(f.order_ts) as order_date,
# MAGIC     COUNT(DISTINCT f.order_number) as total_orders,
# MAGIC     COUNT(*) as total_line_items,
# MAGIC     SUM(f.quantity) as total_quantity,
# MAGIC     SUM(f.line_total) as total_revenue,
# MAGIC     COUNT(DISTINCT f.customer_key) as unique_customers
# MAGIC   FROM lab5.gold.fct_sales_orders f
# MAGIC   GROUP BY DATE(f.order_ts)
# MAGIC )
# MAGIC SELECT 
# MAGIC   dm.order_date,
# MAGIC   d.date_key,
# MAGIC   
# MAGIC   dm.total_orders,
# MAGIC   dm.total_line_items,
# MAGIC   dm.total_quantity,
# MAGIC   dm.unique_customers,
# MAGIC   
# MAGIC   CAST(dm.total_revenue AS DECIMAL(10,2)) as total_revenue,
# MAGIC   CAST(dm.total_revenue / dm.total_orders AS DECIMAL(10,2)) as avg_order_value
# MAGIC   
# MAGIC FROM daily_metrics dm
# MAGIC INNER JOIN lab5.gold.dim_date d 
# MAGIC   ON dm.order_date = d.full_date
# MAGIC ORDER BY dm.order_date;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   'Total customer rows' AS metric,
# MAGIC   CAST(COUNT(*) AS STRING) AS value
# MAGIC FROM lab5.gold.agg_customer_summary
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Unique customer_key' AS metric,
# MAGIC   CAST(COUNT(DISTINCT customer_key) AS STRING) AS value
# MAGIC FROM lab5.gold.agg_customer_summary
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Unique customer_id' AS metric,
# MAGIC   CAST(COUNT(DISTINCT customer_id) AS STRING) AS value
# MAGIC FROM lab5.gold.agg_customer_summary;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   'Total date rows' AS metric,
# MAGIC   CAST(COUNT(*) AS STRING) AS value
# MAGIC FROM lab5.gold.agg_daily_sales
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Unique order_date' AS metric,
# MAGIC   CAST(COUNT(DISTINCT order_date) AS STRING) AS value
# MAGIC FROM lab5.gold.agg_daily_sales
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Min order_date' AS metric,
# MAGIC   CAST(MIN(order_date) AS STRING) AS value
# MAGIC FROM lab5.gold.agg_daily_sales
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC   'Max order_date' AS metric,
# MAGIC   CAST(MAX(order_date) AS STRING) AS value
# MAGIC FROM lab5.gold.agg_daily_sales;
