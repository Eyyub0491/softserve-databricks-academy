# Lab 9 - Databricks REST API / SDK Automation

Lab 9 automates the existing Lab 8 orchestration job using the Databricks
Python SDK (`databricks-sdk`). It triggers the job programmatically, monitors
the run, and reports a clear SUCCESS / FAILURE result with a matching exit
code.

No Lab 5-8 resources are rebuilt or redeployed. Lab 9 only *calls* the
existing orchestration job.

## What the script does

`src/orchestrate_job.py`:

1. Connects to the Databricks workspace using `WorkspaceClient()` (no hardcoded credentials).
2. Triggers the existing Lab 8 job (default id `295471224311110`) with `jobs.run_now`.
3. Captures the returned `run_id`.
4. Polls `jobs.get_run` until the run reaches a terminal life-cycle state (`TERMINATED`, `SKIPPED`, `INTERNAL_ERROR`).
5. Prints each state transition.
6. Reports `SUCCESS` (exit code `0`) when `result_state == SUCCESS`, otherwise `FAILURE` (exit code `1`).

## Authentication

`databricks.sdk.WorkspaceClient` resolves credentials automatically from the
environment. No credentials are stored in the repo:

- Inside a Databricks notebook: workspace-native auth is used automatically.
- Locally / in CI: set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` environment
  variables, or use a `~/.databricks.cfg` CLI profile.

## How to run

From the `week09/lab9_api_automation` directory:

```bash
pip install -r requirements.txt
python src/orchestrate_job.py
```

Options:

```text
--job-id        Databricks job id to trigger (default: 295471224311110)
--poll-interval Seconds between status polls (default: 15)
--timeout       Max seconds to wait before failing (default: unlimited)
```

Example:

```bash
python src/orchestrate_job.py --poll-interval 30 --timeout 1800
```

## Expected status flow

```text
Triggering job 295471224311110 via Databricks Python SDK ...
Started run id=<run_id>; polling every 30s
  run <run_id>: life_cycle_state=PENDING result_state=None
  run <run_id>: life_cycle_state=RUNNING result_state=None
  run <run_id>: life_cycle_state=TERMINATED result_state=SUCCESS
SUCCESS: run <run_id> finished with result_state=SUCCESS
```

On failure the final line becomes `FAILURE: run <run_id> ended with ...` and the
process exits with code `1`.

## Tests

Unit tests mock the SDK client and never touch a real workspace:

```bash
python -m pytest tests -q
```

## CI / CD

`.github/workflows/lab9-ci.yml` provides:

- `static-and-unit`: runs unit tests and compiles sources on push / PR / manual dispatch (no credentials needed).
- `trigger-free-workspace`: a **manually triggered** job (workflow dispatch with
  the `run-real-job` input) that runs the script against the **Free workspace**.
  It uses a GitHub `free-workspace` environment with `DATABRICKS_FREE_HOST` and
  `DATABRICKS_FREE_TOKEN` secrets. **No Academy / prod credentials are used.**

This workflow is separate from the Lab 8 prod-deployment workflow and does not
modify the existing Academy PROD deployment.

## How this satisfies Lab 9

- Uses the Databricks Python SDK (`WorkspaceClient`) to submit and run a job.
- Triggers an existing pipeline/job programmatically and monitors job status.
- Reports status end-to-end with correct exit codes.
- Integrates with CI/CD via a dedicated, manually-triggered workflow for the Free workspace.
