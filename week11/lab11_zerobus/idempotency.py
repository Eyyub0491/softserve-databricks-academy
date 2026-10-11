"""Lab 11 — Idempotent processing layer.

Reads raw events from ``lab5.default.lab11_events`` (the Zerobus
ingestion table, which may contain duplicate physical rows due to
re-delivery) and merges them into ``lab5.default.lab11_events_dedup``
using ``event_id`` as the business/idempotency key.

The MERGE is deterministic and safe to run repeatedly:

* The source query deduplicates raw rows by ``event_id``, keeping the
  most recent delivery (``ROW_NUMBER() … ORDER BY event_time DESC``).
* The MERGE key is ``event_id`` — matched rows are updated in place,
  unmatched rows are inserted.
* Re-running with no new raw events is a no-op (all matches, same data).

Usage (from a Databricks notebook)::

    from idempotency import run_idempotent_processing
    run_idempotent_processing(spark)
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

RAW_TABLE = "lab5.default.lab11_events"
DEDUP_TABLE = "lab5.default.lab11_events_dedup"

MERGE_SQL = f"""
MERGE INTO {DEDUP_TABLE} AS target
USING (
  SELECT event_id, event_type, event_time, producer_id, payload
  FROM (
    SELECT
      event_id,
      event_type,
      event_time,
      producer_id,
      payload,
      ROW_NUMBER() OVER (
        PARTITION BY event_id
        ORDER BY event_time DESC
      ) AS rn
    FROM {RAW_TABLE}
  )
  WHERE rn = 1
) AS source
ON target.event_id = source.event_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
"""


def run_idempotent_processing(spark) -> Dict[str, Any]:
    """Run one pass of idempotent deduplication.

    Returns a dict with ``raw_rows``, ``raw_distinct_ids``,
    ``dedup_rows``, and ``dedup_distinct_ids`` after the MERGE.
    """
    logger.info("Starting idempotent processing  raw=%s  dedup=%s",
               RAW_TABLE, DEDUP_TABLE)

    spark.sql(MERGE_SQL)
    logger.info("MERGE completed.")

    raw_count = spark.sql(
        f"SELECT COUNT(*) AS c FROM {RAW_TABLE}"
    ).collect()[0]["c"]
    raw_distinct = spark.sql(
        f"SELECT COUNT(DISTINCT event_id) AS c FROM {RAW_TABLE}"
    ).collect()[0]["c"]
    dedup_count = spark.sql(
        f"SELECT COUNT(*) AS c FROM {DEDUP_TABLE}"
    ).collect()[0]["c"]
    dedup_distinct = spark.sql(
        f"SELECT COUNT(DISTINCT event_id) AS c FROM {DEDUP_TABLE}"
    ).collect()[0]["c"]

    result = {
        "raw_rows": raw_count,
        "raw_distinct_ids": raw_distinct,
        "dedup_rows": dedup_count,
        "dedup_distinct_ids": dedup_distinct,
    }
    logger.info(
        "Idempotent processing done  raw_rows=%d  raw_distinct=%d  "
        "dedup_rows=%d  dedup_distinct=%d",
        raw_count, raw_distinct, dedup_count, dedup_distinct,
    )
    return result