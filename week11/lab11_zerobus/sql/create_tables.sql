-- Local artifact only: do not execute except during the separately authorized
-- Free-workspace test. This is the confirmed Lab 11 raw target.

CREATE TABLE IF NOT EXISTS lab5.default.lab11_events (
  event_id STRING NOT NULL,
  event_type STRING NOT NULL,
  event_time TIMESTAMP NOT NULL,
  producer_id STRING NOT NULL,
  payload STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS lab5.default.lab11_events_deduplicated (
  event_id STRING NOT NULL,
  event_type STRING NOT NULL,
  event_time TIMESTAMP NOT NULL,
  producer_id STRING NOT NULL,
  payload STRING NOT NULL
)
USING DELTA;

-- Idempotent processing example. Re-running only inserts event IDs not yet
-- present in the curated table. Raw delivery history remains append-oriented.
MERGE INTO lab5.default.lab11_events_deduplicated AS target
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
