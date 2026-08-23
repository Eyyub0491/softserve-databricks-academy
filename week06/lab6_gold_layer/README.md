# Lab 6 - Gold Layer

## Overview

This lab builds the Gold layer for the e-commerce data platform using Databricks.

The Gold layer contains a star schema, business aggregates, governance controls, validation queries, a dashboard, an alert, and a Genie Q&A space.

## Gold Layer

### Dimensions

- `lab5.gold.dim_date` - Date dimension with calendar attributes
- `lab5.gold.dim_customers` - Customer information and loyalty segments
- `lab5.gold.dim_products` - Product information and ordering history

### Fact

- `lab5.gold.fct_sales_orders` - Sales order line items

### Aggregations

- `lab5.gold.agg_customer_summary` - Customer-level sales and lifetime value metrics
- `lab5.gold.agg_daily_sales` - Daily order, revenue, quantity, and customer metrics

## Notebooks

### `01_gold_star_schema`

Creates and validates the Gold star schema:

- Date dimension
- Customer dimension
- Product dimension
- Sales fact table
- Customer summary
- Daily sales summary

### `02_governance`

Implements Unity Catalog governance:

- Schema permissions
- Row-level security
- Column-level masking for `tax_id`
- Governance validation

### `03_validation`

Performs final checks for:

- Dimension row counts
- Fact table integrity
- Key completeness
- Aggregate reconciliation
- Row-level security
- Column-level security

## Dashboard

**Lab 6 - Gold Layer Business Analytics**

The dashboard provides business-level metrics and visualizations including:

- Total revenue
- Total orders
- Customer count
- Average order value
- Daily revenue trend
- Daily orders
- Revenue by state
- Top customers by revenue
- Customers by loyalty segment

## Alert

**Lab 6 - Daily Order Volume Drop Alert**

The alert monitors daily order volume from:

`lab5.gold.agg_daily_sales`

It is used to identify unusually low daily order volumes.

## Genie Q&A

**Lab 6 Gold Layer Business Analytics**

A Genie Q&A space is configured on the Gold layer tables.

Users can ask natural-language questions about:

- Revenue
- Orders
- Customers
- Products
- Loyalty segments
- States
- Daily sales trends

The Genie space uses the Gold tables and their relationships to generate answers without requiring users to write SQL.

## Technologies

- Databricks
- Unity Catalog
- SQL
- Delta Lake
- Lakehouse / Medallion Architecture
- Databricks AI/BI Dashboards
- Genie Q&A
- SQL Alerts

## Data Sources

The Gold layer is built from the existing Silver layer tables:

- `lab5.silver.slv_sales_orders_clean`
- `lab5.silver.slv_customer_dimensions`

## Lab 6 Structure

```text
lab6_gold_layer/
│
├── 01_gold_star_schema
├── 02_governance
├── 03_validation
├── README.md
│
├── Dashboard
│   └── Lab 6 - Gold Layer Business Analytics
│
├── Alert
│   └── Lab 6 - Daily Order Volume Drop Alert
│
└── Genie
    └── Lab 6 Gold Layer Business Analytics
``` 

## Result

The Lab 6 Gold layer provides analytics-ready data with:
- Star schema modeling
- Business aggregates
- Data validation
- Unity Catalog governance
- Row-level security
- Column-level security
- Business dashboard
- Data quality alerting
- Natural-language data exploration with Genie