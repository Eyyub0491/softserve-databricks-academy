# Lab 8: Production Deployment

This bundle brings together the Lakeflow and gold-layer work from Labs 5-7 into one production-oriented Databricks deployment workflow.

## Purpose

The project is designed to coordinate:

- Bronze and Silver ingestion from Lab 5.
- Lab 7 data-quality and quarantine checks.
- The Gold-layer tables, validation logic, and business analytics from Lab 6.
- A single bundle with separate `dev` and `prod` targets.

## Repository layout

```text
week08/lab8_production_deployment/
├── databricks.yml
├── README.md
├── resources/
│   ├── pipelines.yml
│   ├── schemas.yml
│   ├── jobs.yml
│   └── ...
├── src/
│   └── gold/01_gold_star_schema.ipynb
├── dashboards/
├── alerts/
├── governance/
├── tests/
├── .github/workflows/lab8-ci.yml
└── ...
```

## Target environments

- `dev`: `https://dbc-f7231d90-d8a3.cloud.databricks.com`
- `prod`: `https://adb-7405604503619901.1.azuredatabricks.net`

The `dev` and `prod` targets are intentionally separated in the bundle configuration. Catalog and schema values are defined per target, and the workflow is designed to keep the free workspace and Academy workspace distinct.

## Resources managed by the bundle

- Lakeflow pipelines for Bronze and Silver processing.
- Lab 7 validation and quality checks.
- Gold-layer notebook execution with bundle variables for catalog and schema names.
- Schema resources for Bronze, Silver, and Gold namespaces.
- Job orchestration for the production sequence.
- Governance and dashboard/alert references stored as local repository artifacts.

## CI/CD flow

```text
GitHub pull request -> repository checks -> Lab 7 tests -> bundle validation -> target deployment -> verification
```

The GitHub workflow in `.github/workflows/lab8-ci.yml` is used for static validation and the existing test suite. Deployment steps remain separate from the local repository workflow and are only intended for a workspace with the required credentials and ownership.

## Notes

- The bundle intentionally keeps workspace-specific identities and permissions out of the repository until target configuration is known.
- Dashboard and alert definitions remain local references because they currently include hardcoded environment-specific names and IDs.
- The bundle is structured to support a clean promotion from `dev` to `prod` once the target workspaces are configured and authenticated.