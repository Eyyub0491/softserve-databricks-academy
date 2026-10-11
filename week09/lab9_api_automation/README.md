# Lab 9 - Databricks REST API / SDK Automation

Lab 9 automates the existing Lab 8 orchestration job using the Databricks
Python SDK (`databricks-sdk`). It triggers the job programmatically, monitors
the run, and reports a clear SUCCESS / FAILURE result with a matching exit
code.

No Lab 5-8 resources are rebuilt or redeployed. Lab 9 only *calls* the
existing orchestration job. The optional `--serverless-compute-demo` mode
instead provisions a throwaway notebook job on serverless compute and removes
it afterward — it does not touch any permanent resource.

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
  A subprocess launched from a notebook did not inherit the notebook IPython
  authentication context in testing.
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
--job-id                Databricks job id to trigger (default: 295471224311110)
--poll-interval         Seconds between status polls (default: 15)
--timeout               Max seconds to wait before failing (default: unlimited)
--serverless-compute-demo
                        Run a throwaway notebook once on serverless job compute
                        and clean it up (no permanent resources). Mutually exclusive
                        with the default job-trigger behaviour.
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

## Serverless compute demo (`--serverless-compute-demo`)

Instead of triggering the Lab 8 job, this mode demonstrates provisioning and
teardown of compute with the SDK:

1. Creates a throwaway notebook in `~/.lab9_demo_tmp` (per user) using
   `workspace.import_` with base64-encoded `SOURCE` content.
2. Creates a temporary one-task job with **no `job_clusters`**, so it runs on
   **serverless job compute** (same model the Lab 8 job uses).
3. Triggers it with `jobs.run_now` and polls `jobs.get_run` to a terminal state.
4. Deletes the temporary notebook and the temporary job in a `finally` block —
   even on failure — so no permanent Databricks resources are left behind.

Run it:

```bash
python src/orchestrate_job.py --serverless-compute-demo --poll-interval 20
```

Expected output:

```text
Created temporary notebook: /Workspace/Users/<user>/.lab9_demo_tmp/lab9_demo_notebook_<id>
Created temporary serverless job: lab9_serverless_demo_<id> (job_id=<id>)
Started run id=<run_id> on serverless compute; polling every 20s
  run <run_id>: life_cycle_state=RUNNING result_state=None
  run <run_id>: life_cycle_state=TERMINATED result_state=SUCCESS
Cleaned up temporary notebook: /Workspace/Users/<user>/.lab9_demo_tmp/lab9_demo_notebook_<id>
Cleaned up temporary job: <job_id>
SUCCESS: serverless demo run <run_id> finished with result_state=SUCCESS
```

This satisfies the Lab 9 requirement to provision compute, submit a job, and run
a notebook via the REST API / Python SDK, end to end.

## Real Free-workspace end-to-end tests

The automation completed a real end-to-end run in the Free Databricks
workspace. Job `295471224311110` produced run `23448784315770`; its lifecycle
transitioned from `RUNNING` to `TERMINATED` with final result `SUCCESS`. The
automation exited with code `0`.

For that existing-job run, no Databricks resources were created, modified,
deleted, or deployed. The Academy/paid workspace was not used.

The serverless compute demo was later validated separately in the Free
workspace. Temporary job ID `1090868181662400` produced run
`693106553823723`; the run transitioned from `RUNNING` to `TERMINATED` with
result `SUCCESS`, and the script exited with code `0`. Temporary notebook
cleanup and temporary job cleanup were both reported successful. Existing
Lab 8 job `295471224311110` was not touched during this validation.

### Notebook authentication note

Subprocess execution started from a Databricks notebook did not inherit the
notebook's IPython authentication context, so `WorkspaceClient()` in that
subprocess could not rely on the notebook-native credentials. The same
automation logic worked successfully when `WorkspaceClient()` was created
directly in the notebook kernel. The standalone script remains intended for
local or CI execution with its normal environment or CLI-profile credentials.

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
- `--serverless-compute-demo` additionally provisions serverless compute, runs a
  notebook, and tears the temporary resources down via the SDK.
- Integrates with CI/CD via a dedicated, manually-triggered workflow for the Free workspace.

The recorded Free-workspace results verify both the existing-job path and the
separate serverless compute path. The workflow's real-workspace path is opt-in
via manual dispatch and uses only the Free-workspace environment secrets.
