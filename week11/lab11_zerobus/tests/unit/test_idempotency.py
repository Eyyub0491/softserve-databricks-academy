"""Unit tests for the Lab 11 idempotent processing layer.

These tests verify the MERGE SQL structure and the
run_idempotent_processing function using mocked Spark.
Run with:  python -m pytest tests -q
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_SRC = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_SRC))

import idempotency  # noqa: E402


# ---------------------------------------------------------------------------
# MERGE SQL structure
# ---------------------------------------------------------------------------

def test_merge_sql_references_raw_table():
    assert idempotency.RAW_TABLE in idempotency.MERGE_SQL


def test_merge_sql_references_dedup_table():
    assert idempotency.DEDUP_TABLE in idempotency.MERGE_SQL


def test_merge_sql_contains_row_number():
    assert "ROW_NUMBER()" in idempotency.MERGE_SQL


def test_merge_sql_partitions_by_event_id():
    assert "PARTITION BY event_id" in idempotency.MERGE_SQL


def test_merge_sql_orders_by_event_time_desc():
    assert "ORDER BY event_time DESC" in idempotency.MERGE_SQL


def test_merge_sql_filters_to_rn_1():
    assert "WHERE rn = 1" in idempotency.MERGE_SQL


def test_merge_sql_uses_event_id_as_merge_key():
    assert "ON target.event_id = source.event_id" in idempotency.MERGE_SQL


def test_merge_sql_has_when_matched_update():
    assert "WHEN MATCHED THEN UPDATE" in idempotency.MERGE_SQL

def test_merge_sql_has_when_not_matched_insert():
    assert "WHEN NOT MATCHED THEN INSERT" in idempotency.MERGE_SQL


# ---------------------------------------------------------------------------
# run_idempotent_processing (mocked Spark)
# ---------------------------------------------------------------------------

def _mock_spark(counts: dict[str, int]):
    """Create a mock spark where each SQL returns a row with the given count."""
    spark = MagicMock()

    def sql_side_effect(query):
        row = MagicMock()
        # Determine which count to return based on the query
        if "COUNT(DISTINCT event_id)" in query and idempotency.DEDUP_TABLE in query:
            row.__getitem__ = MagicMock(return_value=counts["dedup_distinct"])
        elif "COUNT(DISTINCT event_id)" in query and idempotency.RAW_TABLE in query:
            row.__getitem__ = MagicMock(return_value=counts["raw_distinct"])
        elif idempotency.DEDUP_TABLE in query:
            row.__getitem__ = MagicMock(return_value=counts["dedup_rows"])
        elif idempotency.RAW_TABLE in query:
            row.__getitem__ = MagicMock(return_value=counts["raw_rows"])
        else:
            row.__getitem__ = MagicMock(return_value=0)
        result = MagicMock()
        result.collect.return_value = [row]
        return result

    spark.sql.side_effect = sql_side_effect
    return spark


def test_run_idempotent_processing_returns_correct_metrics():
    spark = _mock_spark({
        "raw_rows": 10,
        "raw_distinct": 5,
        "dedup_rows": 5,
        "dedup_distinct": 5,
    })
    result = idempotency.run_idempotent_processing(spark)
    assert result["raw_rows"] == 10
    assert result["raw_distinct_ids"] == 5
    assert result["dedup_rows"] == 5
    assert result["dedup_distinct_ids"] == 5


def test_run_idempotent_processing_calls_merge_sql():
    spark = _mock_spark({
        "raw_rows": 10, "raw_distinct": 5,
        "dedup_rows": 5, "dedup_distinct": 5,
    })
    idempotency.run_idempotent_processing(spark)
    # The first sql call should be the MERGE
    first_call = spark.sql.call_args_list[0]
    assert "MERGE INTO" in first_call[0][0]


def test_run_idempotent_processing_makes_5_sql_calls():
    spark = _mock_spark({
        "raw_rows": 10, "raw_distinct": 5,
        "dedup_rows": 5, "dedup_distinct": 5,
    })
    idempotency.run_idempotent_processing(spark)
    # 1 MERGE + 4 count queries = 5 total
    assert spark.sql.call_count == 5