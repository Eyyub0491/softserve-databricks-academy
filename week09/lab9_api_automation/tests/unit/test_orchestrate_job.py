"""Unit tests for the Lab 9 orchestration script.

These tests mock the Databricks SDK client so they never touch a real
Databricks workspace. Run with:  python -m pytest tests -q
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Make the src module importable regardless of the current working directory.
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

import orchestrate_job as oj  # noqa: E402


class _FakeState:
    def __init__(self, life_cycle_state, result_state=None):
        self.life_cycle_state = life_cycle_state
        self.result_state = result_state


class _FakeRun:
    def __init__(self, state):
        self.state = state


def _client_with_runs(run_states, run_id=4242):
    """Build a mocked WorkspaceClient whose get_run walks ``run_states``."""
    client = MagicMock()
    client.jobs.run_now.return_value = MagicMock(run_id=run_id)
    client.jobs.get_run.side_effect = [
        _FakeRun(_FakeState(lc, rs)) for lc, rs in run_states
    ]
    return client, run_id


def test_trigger_run_returns_run_id():
    client, expected_run_id = _client_with_runs([])
    assert oj.trigger_run(client, 295471224311110) == expected_run_id
    client.jobs.run_now.assert_called_once_with(job_id=295471224311110)


def test_poll_until_terminal_success():
    states = [("PENDING", None), ("RUNNING", None), ("TERMINATED", "SUCCESS")]
    client, run_id = _client_with_runs(states)
    outcome = oj.poll_until_terminal(client, run_id, poll_interval=0, sleep_fn=lambda _s: None)
    assert outcome.run_id == run_id
    assert outcome.life_cycle_state == "TERMINATED"
    assert outcome.result_state == "SUCCESS"
    assert outcome.is_success is True


def test_poll_until_terminal_failure():
    states = [("RUNNING", None), ("TERMINATED", "FAILED")]
    client, run_id = _client_with_runs(states)
    outcome = oj.poll_until_terminal(client, run_id, poll_interval=0, sleep_fn=lambda _s: None)
    assert outcome.is_success is False
    assert outcome.result_state == "FAILED"


def test_poll_until_terminal_timeout():
    client = MagicMock()
    client.jobs.get_run.return_value = _FakeRun(_FakeState("RUNNING", None))
    times = iter([0.0, 100.0])
    with pytest.raises(TimeoutError):
        oj.poll_until_terminal(
            client,
            run_id=1,
            poll_interval=0,
            timeout=10.0,
            sleep_fn=lambda _s: None,
            monotonic_fn=lambda: next(times),
        )


def test_main_success_exit_zero(monkeypatch, capsys):
    client, _ = _client_with_runs([("RUNNING", None), ("TERMINATED", "SUCCESS")])
    monkeypatch.setattr(oj, "WorkspaceClient", lambda: client)
    rc = oj.main(["--job-id", "1", "--poll-interval", "0"])
    assert rc == 0
    assert "SUCCESS" in capsys.readouterr().out


def test_main_failure_exit_nonzero(monkeypatch, capsys):
    client, _ = _client_with_runs([("RUNNING", None), ("TERMINATED", "FAILED")])
    monkeypatch.setattr(oj, "WorkspaceClient", lambda: client)
    rc = oj.main(["--job-id", "1", "--poll-interval", "0"])
    assert rc == 1
    assert "FAILURE" in capsys.readouterr().out


def test_main_handles_trigger_error(monkeypatch, capsys):
    client = MagicMock()
    client.jobs.run_now.side_effect = RuntimeError("boom")
    monkeypatch.setattr(oj, "WorkspaceClient", lambda: client)
    rc = oj.main(["--job-id", "1", "--poll-interval", "0"])
    assert rc == 1


# ---------------------------------------------------------------------------
# Serverless compute demo (mocked) -- no real Databricks calls
# ---------------------------------------------------------------------------

def _demo_client(run_states, job_id=999, run_id=555):
    """Mocked client for run_serverless_demo."""
    client = MagicMock()
    client.current_user.me.return_value = MagicMock(user_name="demo@example.com")
    client.jobs.create.return_value = MagicMock(job_id=job_id)
    client.jobs.run_now.return_value = MagicMock(run_id=run_id)
    client.jobs.get_run.side_effect = [
        _FakeRun(_FakeState(lc, rs)) for lc, rs in run_states
    ]
    return client


def test_run_serverless_demo_success():
    client = _demo_client([("RUNNING", None), ("TERMINATED", "SUCCESS")])
    outcome = oj.run_serverless_demo(client, poll_interval=0, sleep_fn=lambda _s: None)
    assert outcome.is_success
    assert outcome.run_id == 555
    # temp notebook and temp job are cleaned up
    client.workspace.delete.assert_called_once()
    client.jobs.delete.assert_called_once_with(999)


def test_run_serverless_demo_cleans_up_on_failure():
    client = _demo_client([("RUNNING", None), ("TERMINATED", "FAILED")])
    outcome = oj.run_serverless_demo(client, poll_interval=0, sleep_fn=lambda _s: None)
    assert not outcome.is_success
    assert outcome.result_state == "FAILED"
    client.workspace.delete.assert_called_once()
    client.jobs.delete.assert_called_once_with(999)


def test_run_serverless_demo_cleans_up_even_on_job_create_error():
    client = MagicMock()
    client.current_user.me.return_value = MagicMock(user_name="demo@example.com")
    client.jobs.create.side_effect = RuntimeError("create failed")
    with pytest.raises(RuntimeError):
        oj.run_serverless_demo(client, poll_interval=0, sleep_fn=lambda _s: None)
    # notebook was created before the failing create(); it must still be cleaned up
    client.workspace.delete.assert_called_once()
    client.jobs.delete.assert_not_called()


def test_main_serverless_demo_success(monkeypatch, capsys):
    client = _demo_client([("RUNNING", None), ("TERMINATED", "SUCCESS")])
    monkeypatch.setattr(oj, "WorkspaceClient", lambda: client)
    rc = oj.main(["--serverless-compute-demo", "--poll-interval", "0"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SUCCESS" in out
    assert "serverless" in out.lower()


def test_main_serverless_demo_failure_nonzero(monkeypatch, capsys):
    client = _demo_client([("RUNNING", None), ("TERMINATED", "FAILED")])
    monkeypatch.setattr(oj, "WorkspaceClient", lambda: client)
    rc = oj.main(["--serverless-compute-demo", "--poll-interval", "0"])
    assert rc == 1
    assert "FAILURE" in capsys.readouterr().out
