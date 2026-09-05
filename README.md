# SoftServe Databricks Academy — Data Engineering

This repository contains my work and projects completed during the **SoftServe Databricks Academy**, focused on Data Engineering, Databricks, Azure, and modern cloud data platforms.

## Technologies & Tools

- Databricks
- Azure
- Apache Spark / PySpark
- SQL
- Delta Lake
- Unity Catalog
- Medallion Architecture
- Auto Loader
- Lakeflow
- Zerobus Ingest
- ETL / ELT
- Data Quality & Testing
- Pytest
- DQX
- Git / GitHub
- Azure DevOps
- CI/CD
- Databricks Asset Bundles
- Databricks REST API
- Power BI

## Academy Labs

The Academy covered practical Data Engineering workflows using Databricks and Azure, including:

- Databricks and Azure environment setup
- Unity Catalog and data governance
- Batch and streaming data ingestion
- Auto Loader
- Bronze, Silver, and Gold data layers
- Delta Lake
- Lakeflow Declarative Pipelines
- Data transformation and data quality
- Unit and integration testing
- DQX data quality checks
- Data reconciliation
- CI/CD and DEV → PROD deployment
- Databricks REST API automation
- Lakehouse Federation and CDC
- Zerobus Ingest
- Analytics and Power BI

## Demo Projects

### Demo 1

A team-based Data Engineering project developed as part of the SoftServe Databricks Academy.

The project demonstrates the use of Databricks and modern data engineering practices, including data ingestion, transformation, lakehouse architecture, and analytics.

**My contribution:** Worked on data engineering components, transformations, and project implementation together with the team.

[Demo 1 Repository](<(https://github.com/Eyyub0491/ecommerce-bronze-platform)>)

---

### Demo 2 — E-Commerce Data Platform

An end-to-end e-commerce Data Engineering platform built with Databricks.

The project combines **real-time and batch data processing** using a Medallion Architecture and produces analytics-ready Gold data for reporting.

Key technologies include:

- Databricks
- Apache Spark / PySpark
- Lakeflow
- Zerobus Ingest
- Delta Lake
- Unity Catalog
- Pytest
- DQX
- Azure DevOps
- CI/CD
- Power BI

**My contribution:** Focused mainly on real-time order ingestion with Zerobus, streaming transformations, testing, data quality, and data reconciliation.

[Demo 2 Repository](<(https://github.com/yanquielarango/ecommerce_pipeline_demo/tree/main/ecommerce_pipeline_demo)>)

## Data Engineering Architecture

The projects follow modern lakehouse and Medallion Architecture principles:

```text
Data Sources
     │
     ▼
   Bronze
     │
     ▼
   Silver
     │
     ▼
    Gold
     │
     ▼
 Analytics / Power BI
