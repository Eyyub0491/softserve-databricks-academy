-- Proposed Lab 12 table definitions only; this file has not been executed.
-- Replace <catalog> and <schema> with an approved Unity Catalog target before use.
-- No workspace, principal, permissions, or AI Search index are configured here.

CREATE TABLE IF NOT EXISTS <catalog>.<schema>.raw_documents (
  doc_id STRING NOT NULL,
  source STRING NOT NULL,
  title STRING NOT NULL,
  url STRING NOT NULL,
  content STRING NOT NULL,
  content_sha256 STRING NOT NULL,
  retrieved_at TIMESTAMP,
  ingested_at TIMESTAMP NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS <catalog>.<schema>.document_chunks (
  chunk_id STRING NOT NULL,
  doc_id STRING NOT NULL,
  source STRING NOT NULL,
  title STRING NOT NULL,
  url STRING NOT NULL,
  section STRING,
  chunk_index INT NOT NULL,
  start_char INT NOT NULL,
  end_char INT NOT NULL,
  chunk_text STRING NOT NULL,
  chunk_sha256 STRING NOT NULL,
  chunked_at TIMESTAMP NOT NULL
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');
