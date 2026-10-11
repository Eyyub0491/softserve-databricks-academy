"""Unit tests for the Lab 11 Zerobus producer.

These tests mock the Zerobus SDK and dbutils so they never touch a
real Databricks workspace or require the zerobus package.
Run with:  python -m pytest tests -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make the lab11_zerobus directory importable.
_SRC = Path(__file__).resolve().parents[2]  # lab11_zerobus/
sys.path.insert(0, str(_SRC))

import producer  # noqa: E402


# ---------------------------------------------------------------------------
# _make_event
# ---------------------------------------------------------------------------

def test_make_event_has_all_fields():
    event = producer._make_event(0)
    expected_keys = {"event_id", "event_type", "event_time", "producer_id", "payload"}
    assert set(event.keys()) == expected_keys


def test_make_event_id_is_zero_padded():
    event = producer._make_event(0)
    assert event["event_id"] == "evt_0000"


def test_make_event_id_is_deterministic():
    a = producer._make_event(7)
    b = producer._make_event(7)
    assert a["event_id"] == b["event_id"] == "evt_0007"


def test_make_event_timestamp_is_int_microseconds():
    event = producer._make_event(0)
    assert isinstance(event["event_time"], int)
    # epoch microseconds for late 2026 ≈ 1.79 × 10^15
    assert event["event_time"] > 1_000_000_000_000_000


def test_make_event_payload_is_valid_json():
    event = producer._make_event(3)
    parsed = json.loads(event["payload"])
    assert parsed["source"] == "lab11"
    assert parsed["sequence"] == 3
    assert "metadata" in parsed


def test_make_event_producer_id_is_consistent():
    for i in range(5):
        event = producer._make_event(i)
        assert event["producer_id"] == "lab11-zerobus-producer"


def test_make_event_type_cycles():
    event0 = producer._make_event(0)
    event5 = producer._make_event(5)
    assert event0["event_type"] == event5["event_type"]


# ---------------------------------------------------------------------------
# _get_credentials
# ---------------------------------------------------------------------------

def test_get_credentials_success():
    dbutils = MagicMock()
    dbutils.secrets.get.side_effect = ["client-id-val", "client-secret-val"]
    cid, csec = producer._get_credentials(dbutils)
    assert cid == "client-id-val"
    assert csec == "client-secret-val"


def test_get_credentials_missing_raises():
    dbutils = MagicMock()
    dbutils.secrets.get.return_value = None
    with pytest.raises(RuntimeError, match="Missing credentials"):
        producer._get_credentials(dbutils)


def test_get_credentials_empty_string_raises():
    dbutils = MagicMock()
    dbutils.secrets.get.return_value = ""
    with pytest.raises(RuntimeError, match="Missing credentials"):
        producer._get_credentials(dbutils)


# ---------------------------------------------------------------------------
# run_producer (mocked zerobus SDK)
# ---------------------------------------------------------------------------

def _mock_zerobus():
    """Return a MagicMock that simulates the zerobus SDK module."""
    mock_mod = MagicMock()
    stream = MagicMock()
    stream.ingest_record_offset.return_value = 0
    mock_mod.ZerobusSdk.return_value.create_stream.return_value = stream
    mock_mod.TableProperties.return_value.record_format = "json"
    return mock_mod, stream


def test_run_producer_returns_result_dict():
    mock_mod, stream = _mock_zerobus()
    dbutils = MagicMock()
    dbutils.secrets.get.side_effect = ["cid", "csec"]

    with patch.dict(sys.modules, {"zerobus": mock_mod}):
        result = producer.run_producer(dbutils=dbutils, count=5, start=0)

    assert result["submitted"] == 5
    assert result["acknowledged"] == 5
    assert result["table"] == producer.TABLE_NAME
    assert len(result["events"]) == 5
    assert "duration_s" in result


def test_run_producer_ingests_correct_count():
    mock_mod, stream = _mock_zerobus()
    dbutils = MagicMock()
    dbutils.secrets.get.side_effect = ["cid", "csec"]

    with patch.dict(sys.modules, {"zerobus": mock_mod}):
        producer.run_producer(dbutils=dbutils, count=3, start=10)

    assert stream.ingest_record_offset.call_count == 3
    stream.wait_for_offset.assert_called_once()
    stream.flush.assert_called_once()
    stream.close.assert_called_once()


def test_run_producer_event_ids_match_range():
    mock_mod, stream = _mock_zerobus()
    dbutils = MagicMock()
    dbutils.secrets.get.side_effect = ["cid", "csec"]

    with patch.dict(sys.modules, {"zerobus": mock_mod}):
        result = producer.run_producer(dbutils=dbutils, count=5, start=0)

    ids = [e["event_id"] for e in result["events"]]
    assert ids == ["evt_0000", "evt_0001", "evt_0002", "evt_0003", "evt_0004"]


def test_run_producer_closes_stream_on_success():
    mock_mod, stream = _mock_zerobus()
    dbutils = MagicMock()
    dbutils.secrets.get.side_effect = ["cid", "csec"]

    with patch.dict(sys.modules, {"zerobus": mock_mod}):
        producer.run_producer(dbutils=dbutils, count=1, start=0)

    stream.close.assert_called_once()


def test_run_producer_closes_stream_on_error():
    mock_mod, stream = _mock_zerobus()
    stream.ingest_record_offset.side_effect = RuntimeError("stream error")
    dbutils = MagicMock()
    dbutils.secrets.get.side_effect = ["cid", "csec"]

    with patch.dict(sys.modules, {"zerobus": mock_mod}):
        with pytest.raises(RuntimeError, match="stream error"):
            producer.run_producer(dbutils=dbutils, count=3, start=0)

    # stream.close() must still be called (try/finally)
    stream.close.assert_called_once()


def test_no_hardcoded_secret_in_producer_source():
    """The producer source must not contain any literal secret value."""
    src = Path(_SRC / "producer.py").read_text()
    # Must reference dbutils.secrets.get
    assert "dbutils.secrets.get" in src
    # Must NOT contain hardcoded secret values (not variable names).
    # These match a literal string assigned to a secret-like variable,
    # not a function call like client_secret = _get_credentials(...).
    suspicious = [
        'client_secret = "',
        'client_id = "',
        'secret = "',
        'password = "',
        'token = "',
        'access_token = "',
    ]
    for pattern in suspicious:
        assert pattern not in src, f"Hardcoded secret found: {pattern}"