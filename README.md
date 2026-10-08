# SoftServe Databricks Academy — Data Engineering

This repository contains my work and projects completed during the **SoftServe Databricks Academy**, focused on Data Engineering, Databricks, Azure, and modern cloud data platforms.

## Structure

- Week 01: Databricks Fundamentals & Development Setup
- Week 02: Azure Services & Shared Lakehouse Setup
- Week 03: Streaming & Incremental Ingestion
- Week 04: Silver Layer, Data Quality & Schema Evolution
- Week 05: Declarative Pipelines / Lakeflow
- Week 06: Gold Layer & Business Analytics
- Week 07: Data Quality Testing & Unit Tests
- Week 08: Production Deployment, Orchestration & CI/CD
- Week 09: Databricks REST API Automation
- Week 10: Lakehouse Federation & Change Data Capture (CDC)
- Week 11: Zerobus Ingest & Zero-Bus Streaming

## Technologies & Tools

- Databricks
- Azure
- Apache Spark / PySpark
- SQL
- Delta Lake
- Unity Catalog
- Medallion Architecture
- Auto Loader
- Lakeflow Declarative Pipelines
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
- Databricks SDK
- OAuth / Service Principals
- Power BI
- Production Orchestration
- GitHub Actions

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
- Databricks REST API and SDK automation
- Databricks job orchestration and monitoring
- Lakehouse Federation and CDC
- Zerobus Ingest and event-driven data ingestion
- Idempotent event processing
- Kafka-style versus zero-bus architectures
- Analytics and Power BI
- Production deployment and orchestration
- DEV → PROD deployment with Databricks Asset Bundles
- GitHub Actions CI/CD workflows
- Pipeline dependencies and end-to-end orchestration
- Production dashboard deployment
- Validation and deployment of Databricks resources


## Demo Projects

### Demo 1

A team-based Data Engineering project developed as part of the SoftServe Databricks Academy.

The project demonstrates the use of Databricks and modern data engineering practices, including data ingestion, transformation, lakehouse architecture, and analytics.

**My contribution:** Worked on data engineering components, transformations, and project implementation together with the team.

[Demo 1 Repository](<https://github.com/Eyyub0491/ecommerce-bronze-platform>)

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

[Demo 2 Repository](<https://github.com/yanquielarango/ecommerce_pipeline_demo/tree/main/ecommerce_pipeline_demo>)

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
