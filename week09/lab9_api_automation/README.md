# Lab 9 - Databricks REST API / SDK Automation

Lab 9 uses the Databricks Python SDK (`databricks-sdk`) to trigger and monitor
the existing Lab 8 orchestration job, and to run a separate, harmless notebook
using serverless job compute. The serverless demonstration submits a one-time
notebook task without a cluster specification; Databricks provisions and
manages compute for the run.

No Lab 5-8 resources are rebuilt or redeployed. Lab 9 only *calls* the
existing orchestration job.

## What the script does

`src/orchestrate_job.py` has two paths:

1. Connects to the Databricks workspace using `WorkspaceClient()` (no hardcoded credentials).
2. By default, triggers the existing Lab 8 job (default id `295471224311110`) with `jobs.run_now`.
3. With `--serverless-compute-demo`, uploads a tiny notebook that only prints a message, then submits a one-time notebook run without a cluster specification so the workspace uses managed serverless job compute.
4. Both paths capture the run ID, poll `jobs.get_run` until terminal, print state transitions, and report SUCCESS (exit code `0`) or FAILURE (exit code `1`).
5. The temporary notebook is deleted in `finally`, including setup and submission failures. If monitoring raises an error, the script requests run cancellation before cleanup. Databricks manages serverless compute for the run; it is not a persistent user-created cluster.

The demo uses `jobs.submit`, which creates a one-time run rather than a saved
Jobs resource. There is no persistent job definition for the script to delete;
the run reaches a terminal state (or is cancellation-requested on an error),
and Databricks manages the serverless compute lifecycle.

The serverless demo does not alter Lab 8's orchestration job or its resources.
It demonstrates programmatic submission of a workload that causes Databricks
to provision managed compute, without re-running the Lab 8 data pipeline. The
serverless path requires serverless jobs to be enabled for the workspace and
notebook task type.

## Authentication

`databricks.sdk.WorkspaceClient` resolves credentials automatically from the
environment. No credentials are stored in the repo:

- Inside a Databricks notebook kernel: workspace-native auth can be used. A subprocess launched from a notebook did not inherit the notebook IPython authentication context in testing.
- Locally / in CI: set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` environment
  variables, or use a `~/.databricks.cfg` CLI profile.

## How to run

From the `week09/lab9_api_automation` directory:

```bash
pip install -r requirements.txt
python src/orchestrate_job.py
```

Existing Lab 8 job options:

```text
--job-id        Databricks job id to trigger (default: 295471224311110)
--poll-interval Seconds between status polls (default: 15)
--timeout       Max seconds to wait before failing (default: unlimited)
```

Example:

```bash
python src/orchestrate_job.py --poll-interval 30 --timeout 1800
```

Run only the isolated serverless compute demonstration:

```bash
python src/orchestrate_job.py --serverless-compute-demo --poll-interval 30 --timeout 1800
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
cleanup and temporary job cleanup were both reported successful. The script
uses a one-time `jobs.submit` run, so it does not leave a saved job definition
to delete. Existing Lab 8 job `295471224311110` was not touched during this
validation.

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

The reported validation completed all 12 mocked unit tests successfully.

## CI / CD

`.github/workflows/lab9-ci.yml` provides:

- `static-and-unit`: runs unit tests and compiles sources on push / PR / manual dispatch (no credentials needed).
- `trigger-free-workspace`: a **manually triggered** job (workflow dispatch with
  the `run-serverless-demo` input) that runs only the serverless compute demonstration against the **Free workspace**.
  It uses a GitHub `free-workspace` environment with `DATABRICKS_FREE_HOST` and
  `DATABRICKS_FREE_TOKEN` secrets. **No Academy / prod credentials are used.**

This workflow is separate from the Lab 8 prod-deployment workflow and does not
modify the existing Academy PROD deployment.

## How this satisfies Lab 9

- Uses the Databricks Python SDK (`WorkspaceClient`) to submit and run a job.
- Triggers an existing job programmatically and monitors its status.
- Submits a no-write notebook on managed serverless job compute and monitors its status end-to-end.
- Reports status end-to-end with correct exit codes.
- Integrates with CI/CD via a dedicated, manually-triggered workflow for the Free workspace.

The recorded Free-workspace results verify both the existing-job path and the
separate serverless compute path. The workflow's real-workspace path is opt-in via manual
dispatch and uses only the Free-workspace environment secrets.
