#!/usr/bin/env python3
"""Lab 9 - Databricks REST API / SDK automation.

Trigger the existing Lab 8 orchestration job (id 295471224311110) in the Free
Databricks workspace, poll the run until it reaches a terminal state, and
report SUCCESS or FAILURE with a proper exit code.

With ``--serverless-compute-demo`` it instead creates a throwaway notebook,
runs it once on serverless job compute (no permanent resources), polls the
run, and deletes the temporary notebook and job afterward.

Authentication
--------------
``databricks.sdk.WorkspaceClient`` resolves credentials automatically from the
local environment -- ``DATABRICKS_HOST`` / ``DATABRICKS_TOKEN`` environment
variables, a ``~/.databricks.cfg`` CLI profile, or the workspace-native auth
used when the script is executed inside a Databricks notebook. No credentials
are hardcoded in this script.
"""

from __future__ import annotations

import argparse
import base64
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import NotebookTask, Source, Task
from databricks.sdk.service.workspace import ImportFormat, Language

# Existing Lab 8 orchestration job in the Free workspace.
DEFAULT_JOB_ID = 295471224311110

# Life-cycle states after which a run will not change anymore.
TERMINAL_LIFECYCLE_STATES = {"TERMINATED", "SKIPPED", "INTERNAL_ERROR"}
SUCCESS_RESULT_STATE = "SUCCESS"

# Source of the throwaway notebook used by --serverless-compute-demo.
DEMO_NOTEBOOK_SOURCE = """# Databricks notebook source
print("Lab 9 serverless compute demo: starting")
# COMMAND ----------
rows = spark.range(100).count()
print("Lab 9 serverless compute demo: spark.range(100).count() =", rows)
# COMMAND ----------
print("Lab 9 serverless compute demo: completed")
"""


@dataclass
class RunOutcome:
    """Final, terminal outcome of a job run."""

    run_id: int
    life_cycle_state: str
    result_state: Optional[str]

    @property
    def is_success(self) -> bool:
        return self.result_state == SUCCESS_RESULT_STATE


def _state_name(state) -> Optional[str]:
    """Return a comparable string name for a (possibly enum) state value."""
    if state is None:
        return None
    value = getattr(state, "value", None)
    return value if value is not None else str(state)


def trigger_run(client: WorkspaceClient, job_id: int) -> int:
    """Trigger ``job_id`` and return the resulting run id."""
    response = client.jobs.run_now(job_id=job_id)
    run_id = getattr(response, "run_id", None)
    if run_id is None:
        raise RuntimeError("run_now() did not return a run id")
    return int(run_id)


def poll_until_terminal(
    client: WorkspaceClient,
    run_id: int,
    poll_interval: float = 15.0,
    timeout: Optional[float] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> RunOutcome:
    """Poll ``run_id`` until it reaches a terminal life-cycle state.

    Prints each state transition. Raises ``TimeoutError`` if ``timeout`` is
    set and exceeded.
    """
    start = monotonic_fn()
    last_life_cycle: Optional[str] = None

    while True:
        run = client.jobs.get_run(run_id=run_id)
        state = getattr(run, "state", None)
        life_cycle = _state_name(getattr(state, "life_cycle_state", None)) or "UNKNOWN"
        result = _state_name(getattr(state, "result_state", None))

        if life_cycle != last_life_cycle:
            print(f"  run {run_id}: life_cycle_state={life_cycle} result_state={result}")
            last_life_cycle = life_cycle

        if life_cycle in TERMINAL_LIFECYCLE_STATES:
            return RunOutcome(run_id=run_id, life_cycle_state=life_cycle, result_state=result)

        if timeout is not None and (monotonic_fn() - start) > timeout:
            raise TimeoutError(
                f"run {run_id} did not reach a terminal state within {timeout:.0f}s "
                f"(last state: {life_cycle})"
            )

        sleep_fn(poll_interval)


def run_job_and_wait(
    client: WorkspaceClient,
    job_id: int,
    poll_interval: float = 15.0,
    timeout: Optional[float] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> RunOutcome:
    """Trigger a job and block until its run reaches a terminal state."""
    print(f"Triggering job {job_id} via Databricks Python SDK ...")
    run_id = trigger_run(client, job_id)
    print(f"Started run id={run_id}; polling every {poll_interval:.0f}s")
    return poll_until_terminal(client, run_id, poll_interval, timeout, sleep_fn, monotonic_fn)


# ---------------------------------------------------------------------------
# Serverless compute demo (--serverless-compute-demo)
# ---------------------------------------------------------------------------

DEMO_JOB_TIMEOUT_SECONDS = 600


def _demo_tmp_dir(client: WorkspaceClient) -> str:
    """Return a per-user workspace directory used for throwaway demo notebooks."""
    user = client.current_user.me().user_name
    return f"/Workspace/Users/{user}/.lab9_demo_tmp"


def run_serverless_demo(
    client: WorkspaceClient,
    poll_interval: float = 15.0,
    timeout: Optional[float] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> RunOutcome:
    """Create a throwaway notebook, run it once on serverless job compute, poll
    the run to a terminal state, then delete the temporary notebook and job.

    No permanent Databricks resources are created: both the notebook and the
    one-off job are removed in the ``finally`` block, even on failure.
    """
    parent_dir = _demo_tmp_dir(client)
    suffix = uuid.uuid4().hex[:8]
    notebook_path = f"{parent_dir}/lab9_demo_notebook_{suffix}"
    job_name = f"lab9_serverless_demo_{suffix}"
    job_id: Optional[int] = None
    notebook_created = False

    try:
        client.workspace.mkdirs(parent_dir)
        client.workspace.import_(
            notebook_path,
            content=base64.b64encode(DEMO_NOTEBOOK_SOURCE.encode("utf-8")).decode("utf-8"),
            format=ImportFormat.SOURCE,
            language=Language.PYTHON,
            overwrite=True,
        )
        notebook_created = True
        print(f"Created temporary notebook: {notebook_path}")

        job = client.jobs.create(
            name=job_name,
            tasks=[
                Task(
                    task_key="lab9_demo_notebook",
                    notebook_task=NotebookTask(
                        notebook_path=notebook_path,
                        source=Source.WORKSPACE,
                    ),
                )
            ],
            max_concurrent_runs=1,
            timeout_seconds=DEMO_JOB_TIMEOUT_SECONDS,
            tags={"lab": "9", "ephemeral": "true"},
        )
        job_id = job.job_id
        print(f"Created temporary serverless job: {job_name} (job_id={job_id})")

        run_id = trigger_run(client, job_id)
        print(f"Started run id={run_id} on serverless compute; polling every {poll_interval:.0f}s")
        return poll_until_terminal(client, run_id, poll_interval, timeout, sleep_fn, monotonic_fn)
    finally:
        if notebook_created:
            try:
                client.workspace.delete(notebook_path)
                print(f"Cleaned up temporary notebook: {notebook_path}")
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: failed to delete temp notebook {notebook_path}: {exc}", file=sys.stderr)
        if job_id is not None:
            try:
                client.jobs.delete(job_id)
                print(f"Cleaned up temporary job: {job_id}")
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: failed to delete temp job {job_id}: {exc}", file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lab 9: trigger and monitor a Databricks job via the Python SDK.",
    )
    parser.add_argument("--job-id", type=int, default=DEFAULT_JOB_ID, help="Databricks job id to trigger")
    parser.add_argument("--poll-interval", type=float, default=15.0, help="Seconds between status polls")
    parser.add_argument("--timeout", type=float, default=None, help="Max seconds to wait before failing (default: unlimited)")
    parser.add_argument(
        "--serverless-compute-demo",
        action="store_true",
        help="Run a throwaway notebook once on serverless job compute and clean it up (no permanent resources)",
    )
    args = parser.parse_args(argv)

    client = WorkspaceClient()
    try:
        if args.serverless_compute_demo:
            outcome = run_serverless_demo(
                client,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
            )
        else:
            outcome = run_job_and_wait(
                client,
                job_id=args.job_id,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure as a non-zero exit
        print(f"FAILURE: {exc}", file=sys.stderr)
        return 1

    if outcome.is_success:
        label = "serverless demo run" if args.serverless_compute_demo else "run"
        print(f"SUCCESS: {label} {outcome.run_id} finished with result_state={outcome.result_state}")
        return 0

    print(
        f"FAILURE: run {outcome.run_id} ended with "
        f"life_cycle_state={outcome.life_cycle_state} result_state={outcome.result_state}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
