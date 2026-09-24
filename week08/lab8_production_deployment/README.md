# Lab 8 - Production Deployment

This lab brings together the Lakeflow work from Lab 5 and the testing/data-quality work from Lab 7 into a simple Databricks Asset Bundle for a dev/prod deployment flow. The main idea is to package the resources in one place, keep environment-specific values separate, and let GitHub Actions handle the production deployment path.

This README is intentionally kept as the project reference for the bundle and CI flow; any change here is only to keep the Lab 8 project visible to the repo-triggered GitHub Actions workflow.

## Purpose

The project keeps the Lab 5 and Lab 7 outputs in a reusable bundle and adds a Lab 8 Gold-layer workflow that can run against different workspaces. The bundle defines the catalog, schema, and dashboard settings for each target instead of hard-coding one workspace.

The structure is meant to support:

- a local `dev` target for validation
- a separate `prod` target for the production workspace
- repeated deployment logic with target-specific variables
- GitHub-based validation and deployment checks

## Bundle structure

The root bundle is defined in `databricks.yml`. It syncs the Lab 5 and Lab 7 folders together with the current Lab 8 project, and it includes all resource YAML files under `resources/`.

The bundle declares these variables:

- `catalog`
- `bronze_schema`
- `silver_schema`
- `gold_schema`
- `warehouse_id`

These values are set differently for the `dev` and `prod` targets.

## Targets

### `dev`

- Host: https://dbc-f7231d90-d8a3.cloud.databricks.com
- Default target
- Catalog: `lab5`
- Bronze schema: `bronze`
- Silver schema: `silver`
- Gold schema: `gold`
- Dashboard file: `dashboards/Lab 8 - Gold Layer Business Analytics.lvdash.json`

### `prod`

- Host: https://adb-7405604503619901.1.azuredatabricks.net
- Catalog: `dbr_dev`
- Bronze schema: `ayyuborujzade_bronze`
- Silver schema: `ayyuborujzade_silver`
- Gold schema: `ayyuborujzade_gold`
- Dashboard file: `dashboards/Lab 8 - Gold Layer Business Analytics - PROD.lvdash.json`

The workspaces are intentionally kept separate, and the target-specific `file_path` setting in `databricks.yml` switches which dashboard JSON is attached for each environment.

## Deployed resources

The bundle includes the main resources below.

### Schemas

`resources/schemas.yml` creates the Bronze, Silver, and Gold schemas in the target catalog.

### Pipelines

`resources/pipelines.yml` defines:

- `lab5_lakeflow_pipeline`
- `lab7_pipeline`

These point to the Lab 5 Lakeflow pipeline files and the Lab 7 Lakeflow job file.

### Job orchestration

`resources/jobs.yml` defines `lab8_production_orchestration`.

The job runs in this order:

1. `lab5_lakeflow`
2. `lab7_data_quality`
3. `gold_star_schema`

The final step runs the notebook `src/gold/01_gold_star_schema.ipynb` with the target catalog and schema parameters.

### Gold notebook

`src/gold/01_gold_star_schema.ipynb` is the Lab 8 parameterized version of the Gold star-schema transformation. It uses notebook widgets for the catalog and schema names so the same notebook can run in different targets.

### Dashboards

`resources/dashboard.yml` registers the dashboard resource with the bundle and sets the warehouse ID and parent path. The actual dashboard file is selected from `databricks.yml` depending on the target.

## Why there are two dashboard files

The two dashboard JSON files are kept because the underlying data source names are different in each environment.

- The DEV dashboard sources point to `lab5.gold.agg_daily_sales` and `lab5.gold.agg_customer_summary`.
- The PROD dashboard sources point to `dbr_dev.ayyuborujzade_gold.agg_daily_sales` and `dbr_dev.ayyuborujzade_gold.agg_customer_summary`.

The dashboard JSON is static, so the bundle uses a target-specific dashboard file path instead of trying to parameterize the source table names inside the exported dashboard JSON. This is the safest simple approach for the current setup.

## CI/CD flow

The workflow is defined in `.github/workflows/lab8-ci.yml`.

### Pull request flow

On pull requests, the workflow:

- checks out the repo
- sets up Python and installs the Lab 7 test dependencies
- installs the Databricks CLI
- validates YAML, JSON, and notebook structure
- runs the non-integration Lab 7 pytest suite
- runs `databricks bundle validate --target dev`

### Main branch flow

On pushes to the `main` branch, the workflow repeats the repo checks and runs `databricks bundle deploy --target prod` using GitHub Actions secrets:

- `DATABRICKS_PROD_HOST`
- `DATABRICKS_PROD_TOKEN`

This is the intended production deployment path for Lab 8.

## Intended deployment flow

The project is intended to work like this:

1. Validate the repo and bundle locally or in PR checks.
2. Use the `dev` target for routine validation and bundle checks.
3. Use the `prod` target only for the production workspace deployment path.
4. Keep environment-specific catalog names, schema names, and dashboard files separate by target.
5. Handle workspace-specific permissions and governance setup in the target workspace rather than assuming they are fully represented in the repo.

This is a bundle-oriented lab project, not a fully managed enterprise deployment system. The code is structured to be practical and portable across the two Databricks environments it defines.

## Project structure

```text
lab8_production_deployment/
├── .github/
│   └── workflows/
│       └── lab8-ci.yml
├── dashboards/
│   ├── Lab 8 - Gold Layer Business Analytics.lvdash.json
│   ├── Lab 8 - Gold Layer Business Analytics - PROD.lvdash.json
│   └── README.md
├── governance/
│   └── README.md
├── resources/
│   ├── dashboard.yml
│   ├── jobs.yml
│   ├── pipelines.yml
│   └── schemas.yml
├── src/
│   └── gold/
│       └── 01_gold_star_schema.ipynb
├── tests/
│   └── README.md
├── databricks.yml
├── README.md
```

This project is intentionally kept small and focused on the bundle, deployment flow, and target-specific configuration needed for a Lab 8 handoff.