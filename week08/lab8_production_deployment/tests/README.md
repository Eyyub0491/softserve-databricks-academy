# Testing and CI/CD Strategy

Lab 8 reuses the existing Lab 7 test suite instead of copying it into a second location. The source of truth remains in `week07/lab7_testing_dq/tests`.

## Reused coverage

- Unit tests for transformation utilities, dates, business logic, and validation helpers.
- Data-quality checks for completeness, uniqueness, validity, freshness, and reconciliation.
- Databricks Connect integration tests when a live target is available.
- DQX validation for Silver and Gold expectations.

The repository keeps the Lab 7 `pytest.ini`, `conftest.py`, dependency list, and integration markers as the authoritative test configuration.

## Local validation for Lab 8

The bundle checks should cover:

- YAML syntax for the bundle and resource files.
- Notebook JSON structure and code-cell syntax.
- Local resource references and repository paths.
- Absence of hardcoded credentials or tokens.

The workflow in `.github/workflows/lab8-ci.yml` performs these static checks and then runs the existing non-integration Lab 7 tests.

## CI/CD flow

```text
GitHub pull request -> repository checks -> existing tests -> bundle validation -> target deployment -> smoke verification
```

The deployment path is intentionally separated from the local repository checks. For a real workspace deployment, CI must provide the appropriate Databricks credentials and a target-specific deployment context.

## Follow-up work

- Add a dedicated workflow for the consolidated root bundle once deployment ownership is defined.
- Secure `dev` and `prod` authentication through CI secrets or federation.
- Add a protected deployment path for the production target.
- Decide when Databricks Connect integration tests should run in CI.
