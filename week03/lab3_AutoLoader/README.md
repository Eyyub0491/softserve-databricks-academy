# Lab 3 — Streaming & Incremental Ingestion (Auto Loader + Event Hub)

Databricks lab covering incremental ingestion with Auto Loader, schema evolution, and real-time streaming ingestion from Azure Event Hub using Spark Structured Streaming.

## Folder structure

```
week03/lab3_AutoLoader/
├── Lab3_AutoLoader.ipynb           # Stage 1: Auto Loader + Structured Streaming
├── Lab3_EventHub_Producer.ipynb    # Stage 2a: sends synthetic events to Event Hub
├── Lab3_EventHub_Consumer.ipynb    # Stage 2b: reads from Event Hub into the bronze layer
└── README.md
```

## What each notebook does

**`Lab3_AutoLoader.ipynb`**
Generates ~10k synthetic click events, writes them as 1,000 small JSON files, and ingests them incrementally with Auto Loader (`cloudFiles`). Covers:
- schema inference, `schemaLocation`, and `schemaEvolutionMode = "addNewColumns"`
- handling a newly added source column (`country`) without the pipeline failing outright
- the `_rescued_data` column, including why it stays empty until a real type conflict exists
- per-batch streaming stats via `DESCRIBE HISTORY`
- comparing `availableNow` vs `processingTime` triggers
- a checkpoint-based reload test (safe rerun vs. deleting the checkpoint)

**`Lab3_EventHub_Producer.ipynb`**
Publishes synthetic JSON events (`event_id`, `event_type`, `user_id`, `timestamp`) to the shared Azure Event Hub using `azure-eventhub`, spaced out to simulate a live stream rather than a single burst.

**`Lab3_EventHub_Consumer.ipynb`**
Reads from Event Hub via its Kafka-compatible endpoint, parses the JSON payload with `from_json`, adds streaming metadata (partition, offset, Event Hub timestamp, ingestion timestamp), and writes to a Delta bronze table. Includes a checkpoint-based restart test and a discussion of at-least-once vs. exactly-once semantics.

## Prerequisites

- Databricks workspace access (`dbr_dev` catalog, or update the catalog/schema names in the notebooks to your own)
- Access to the cohort's shared Azure Event Hub (`ayyuborujzade_evh` on `evhpl24databricks.servicebus.windows.net`)
- `azure-eventhub` Python package (installed automatically in the producer notebook via `%pip install`)

## Setup — Event Hub credentials

The Event Hub connection string is **not** stored in either notebook. Both the producer and consumer read it from a Databricks widget at runtime:

```python
connection_string = dbutils.widgets.get("eventhub_connection_string")
```

Before running either notebook, set the widget value to the connection string, either:
- via the widget field at the top of the notebook in the Databricks UI, or
- by running `dbutils.widgets.text("eventhub_connection_string", "<your connection string>")` once interactively

Never hardcode the connection string in a cell or print it — either leaks the `SharedAccessKey` into notebook source or output history.

## How to run

1. Run `Lab3_AutoLoader.ipynb` top to bottom — self-contained, no external dependencies beyond the workspace volumes it creates/resets.
2. Run `Lab3_EventHub_Producer.ipynb` to publish a batch of events to the Event Hub (set the connection string widget first).
3. Run `Lab3_EventHub_Consumer.ipynb` to ingest those events into the bronze Delta table (set the connection string widget first).
4. To test safe reload behavior, rerun the consumer notebook without deleting `checkpoint_path` — row counts should stay flat. Deleting the checkpoint before rerunning will reprocess everything and duplicate rows, which is expected and demonstrated in-notebook.

## Done-when checklist

- [x] Auto Loader ingests incrementally (`availableNow` trigger, confirmed via `DESCRIBE HISTORY`)
- [x] A newly added source column is handled via schema evolution without failing
- [x] Checkpoint-based reload works safely (same checkpoint → no duplicates; deleted checkpoint → duplicates, on purpose)
- [x] Producer sends synthetic events to the shared Event Hub
- [x] Consumer reads via Spark Structured Streaming and lands data in the bronze schema with metadata
- [x] UDFs avoided where a built-in expression (`from_json`) does the job
