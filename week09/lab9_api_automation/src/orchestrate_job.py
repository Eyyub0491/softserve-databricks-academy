#!/usr/bin/env python3
"""Lab 9 - Databricks REST API / SDK automation.

Trigger the existing Lab 8 orchestration job (id 295471224311110) in the Free
Databricks workspace, poll the run until it reaches a terminal state, and
report SUCCESS or FAILURE with a proper exit code.

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
from databricks.sdk.service.jobs import (
    NotebookTask,
    SubmitTask,
)
from databricks.sdk.service.workspace import ImportFormat, Language

# Existing Lab 8 orchestration job in the Free workspace.
DEFAULT_JOB_ID = 295471224311110

# Life-cycle states after which a run will not change anymore.
TERMINAL_LIFECYCLE_STATES = {"TERMINATED", "SKIPPED", "INTERNAL_ERROR"}
SUCCESS_RESULT_STATE = "SUCCESS"
DEMO_NOTEBOOK_SOURCE = '''# Databricks notebook source\nprint("Lab 9 serverless job compute is running")\n'''


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


def run_serverless_compute_demo(
    client: WorkspaceClient,
    poll_interval: float = 15.0,
    timeout: Optional[float] = None,
) -> RunOutcome:
    """Submit a notebook-only run so Databricks uses managed serverless compute."""
    user = client.current_user.me().user_name
    notebook_path = f"/Users/{user}/.lab9/serverless_compute_demo_{uuid.uuid4().hex}.py"
    run_id = None
    try:
        client.workspace.mkdirs(path=f"/Users/{user}/.lab9")
        client.workspace.import_(
            path=notebook_path,
            format=ImportFormat.SOURCE,
            language=Language.PYTHON,
            content=base64.b64encode(DEMO_NOTEBOOK_SOURCE.encode()).decode(),
            overwrite=True,
        )
        response = client.jobs.submit(
            run_name="lab9_serverless_compute_demo",
            tasks=[SubmitTask(
                task_key="serverless_notebook",
                notebook_task=NotebookTask(notebook_path=notebook_path),
            )],
        )
        run_id = getattr(response, "run_id", None)
        if run_id is None:
            raise RuntimeError("jobs.submit() did not return a run id")
        print(f"Submitted ephemeral compute demo run {run_id}")
        try:
            return poll_until_terminal(client, int(run_id), poll_interval, timeout)
        except Exception:
            try:
                client.jobs.cancel_run(run_id=int(run_id))
            except Exception as cancel_error:  # noqa: BLE001
                print(f"Could not cancel run {run_id}: {cancel_error}", file=sys.stderr)
            raise
    finally:
        client.workspace.delete(path=notebook_path)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lab 9: trigger and monitor a Databricks job via the Python SDK.",
    )
    parser.add_argument("--job-id", type=int, default=DEFAULT_JOB_ID, help="Databricks job id to trigger")
    parser.add_argument("--poll-interval", type=float, default=15.0, help="Seconds between status polls")
    parser.add_argument("--timeout", type=float, default=None, help="Max seconds to wait before failing (default: unlimited)")
    parser.add_argument("--serverless-compute-demo", action="store_true", help="Run a no-write notebook using managed serverless job compute instead of the existing Lab 8 job")
    args = parser.parse_args(argv)

    client = WorkspaceClient()
    try:
        if args.serverless_compute_demo:
            outcome = run_serverless_compute_demo(
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
        print(f"SUCCESS: run {outcome.run_id} finished with result_state={outcome.result_state}")
        return 0

    print(
        f"FAILURE: run {outcome.run_id} ended with "
        f"life_cycle_state={outcome.life_cycle_state} result_state={outcome.result_state}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
