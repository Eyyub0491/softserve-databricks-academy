-- Lab 11 — Zero-Bus Streaming with Zerobus
-- DDL for the raw ingestion table and the deduplicated table.
-- Run in a Databricks notebook or SQL editor.
-- Local artifact only: do not execute except during the separately authorized
-- Free-workspace test.

-- ---------------------------------------------------------------------------
-- Raw table: receives events directly from Zerobus Ingest.
-- Duplicate physical rows are expected (re-delivery is normal).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lab5.default.lab11_events (
  event_id    STRING NOT NULL,
  event_type  STRING NOT NULL,
  event_time  TIMESTAMP NOT NULL,
  producer_id STRING NOT NULL,
  payload     STRING NOT NULL
) USING DELTA;

-- ---------------------------------------------------------------------------
-- Deduplicated table: one logical row per event_id.
-- Populated by the idempotent MERGE in idempotency.py.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lab5.default.lab11_events_dedup (
  event_id    STRING NOT NULL,
  event_type  STRING NOT NULL,
  event_time  TIMESTAMP NOT NULL,
  producer_id STRING NOT NULL,
  payload     STRING NOT NULL
) USING DELTA;

-- Idempotent processing example. Re-running only inserts event IDs not yet
-- present in the curated table. Raw delivery history remains append-oriented.
MERGE INTO lab5.default.lab11_events_dedup AS target
USING (
  SELECT event_id, event_type, event_time, producer_id, payload
  FROM (
    SELECT *, ROW_NUMBER() OVER (
      PARTITION BY event_id ORDER BY event_time ASC
    ) AS duplicate_rank
    FROM lab5.default.lab11_events
  ) ranked
  WHERE duplicate_rank = 1
) AS source
ON target.event_id = source.event_id
WHEN NOT MATCHED THEN INSERT (
  event_id, event_type, event_time, producer_id, payload
) VALUES (
  source.event_id, source.event_type, source.event_time,
  source.producer_id, source.payload
);
