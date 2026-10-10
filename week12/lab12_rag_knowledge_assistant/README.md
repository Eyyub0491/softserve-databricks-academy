# Lab 12 — RAG Knowledge Assistant

This project is a small RAG application over an allowlist of public Python
documentation pages. Its local unit tests use fixtures and fake SDK/Spark
clients; they do not fetch documents, connect to Databricks, create embeddings,
or call a model endpoint.

## Implemented locally

- `documents.py`, `chunking.py`, and `ingestion.py` fetch and parse the
  allowlisted pages, preserve source/section/offset metadata, and prepare table
  rows. Fetches occur only when `run_ingestion()` is called.
- `reconciliation.py` plans keyed upserts and stale-chunk removals.
- `delta_writer.py` persists a plan to existing Delta tables using an injected
  Spark session. `runtime.run_ingestion()` reads the current table snapshots,
  plans changes, and invokes the writer. It does not create tables or an index.
- `DatabricksVectorSearchRetriever` queries a managed-embedding Delta Sync
  index. `DatabricksServingChatModel` calls a configured Databricks Model
  Serving endpoint through the SDK `serving_endpoints_data_plane.query()`
  operation. `runtime.create_runtime()`
  wires those adapters; `Lab12Runtime.answer()` runs a RAG query.
- `Lab12Runtime.evaluate()` runs a fixed set of `EvaluationCase`s through both
  RAG and no-retrieval workflows and returns side-by-side results. It does not
  write evaluation data or compute a quality score.

The model adapter uses temperature `0` for comparison consistency, but model
responses are not guaranteed to be deterministic. Each evaluation case can
make up to two model calls (RAG and baseline), which can incur serving costs.
Source references identify retrieved metadata; they do not establish that an
answer is factually supported. The baseline uses the same model without context.

## Offline local setup and tests

Use Python 3.10 or newer. From this directory, install dependencies only if
needed, then run:

```powershell
python -m pip install -r requirements.txt
python -m pytest -p no:cacheprovider tests/unit -q
```

The tests do not require network access, Databricks credentials, or a running
workspace. The SDK adapters are tested with mocked clients.

## Databricks setup — provisioning, performed separately

No tables, serving endpoints, or AI Search resources are provisioned by the
Python runtime. Use a Unity Catalog-enabled workspace with the required
serverless/AI Search availability and privileges. Confirm that the selected
Free/DEV workspace offers those features before proceeding.

1. Select an approved catalog and schema; grant the testing principal the
   required table and AI Search permissions.
2. Replace `<catalog>` and `<schema>` in `sql/create_tables.sql` and execute
   the DDL once. The `document_chunks` Delta table enables legacy change data
   feed, required by standard AI Search Delta Sync indexes unless table row
   tracking provides CDF automatically. The raw document table does not need
   CDF for this application.
3. Create an AI Search standard endpoint and a **managed-embedding Delta Sync**
   index over `document_chunks`, using `chunk_id` as the index key and
   `chunk_text` as the embedding source. Set the index name as a three-part
   catalog/schema/index identifier. Wait until index creation/synchronization
   is complete. For a triggered-sync index, synchronize it after ingestion
   before querying; a continuous-sync index updates from table changes.
4. Create or select a chat-capable Model Serving endpoint and grant the
   workspace principal permission to query it. This project does not provision
   or choose a model endpoint.
5. In a Databricks notebook or runtime, set the non-secret settings below.
   Use the Databricks SDK's configured authentication; do not put tokens or
   passwords in source or environment files committed to Git.

```python
import os

os.environ["LAB12_CATALOG"] = "your_catalog"
os.environ["LAB12_SCHEMA"] = "your_schema"
os.environ["LAB12_VECTOR_SEARCH_INDEX_NAME"] = (
    "your_catalog.your_schema.document_chunks_index"
)
os.environ["LAB12_CHAT_SERVING_ENDPOINT"] = "your-chat-endpoint"
os.environ["LAB12_RETRIEVAL_TOP_K"] = "5"
os.environ["LAB12_CHAT_MAX_TOKENS"] = "512"
```

The environment settings are also readable by `Lab12Config.from_env()`.
`LAB12_CATALOG` and `LAB12_SCHEMA` name the existing target tables; the index
and serving endpoint are separate resources. No credentials are read from
Lab 12 environment variables.

## Databricks execution — explicit operations

Run ingestion only when you intend to fetch the public pages and write Delta
rows. This uses outbound requests to `docs.python.org` and updates the existing
tables; inspect the returned per-URL failures before continuing.

```python
from src.lab12_rag.runtime import run_ingestion

ingestion_run = run_ingestion(spark)
print(ingestion_run.persistence.completed_steps)
print(ingestion_run.prepared.failures)
```

For a triggered-sync index, synchronize it now in the AI Search UI/API and wait
for completion. No index synchronization is performed automatically by
`run_ingestion()`.

Ordinary query execution does not fetch documents or write tables:

```python
from src.lab12_rag.runtime import create_runtime

assistant = create_runtime()
result = assistant.answer("How does Python's pathlib represent paths?")
print(result.answer)
print(result.source_references)
```

To compare a fixed query set, run:

```python
from src.lab12_rag.evaluation import EvaluationCase

comparisons = assistant.evaluate(
    [
        EvaluationCase(
            case_id="pathlib-1",
            query="How does Python's pathlib represent paths?",
        ),
        EvaluationCase(
            case_id="json-1",
            query="How do I parse JSON in Python?",
        ),
    ]
)
for comparison in comparisons:
    print(comparison.case.case_id)
    print("RAG:", comparison.rag.answer)
    print("Baseline:", comparison.baseline.answer)
```

Results are returned in memory only. The evaluation is a side-by-side
comparison, not an automatic factuality or quality judgement.

## Databricks constraints and write guarantees

The SQL declares `NOT NULL` fields, which Databricks enforces. It deliberately
does not declare primary keys: Databricks documents primary and foreign keys
as informational, not uniqueness enforcement. The writer validates duplicate
keys in an incoming plan and checks for duplicate target keys that overlap the
current upsert batch. Deterministic IDs and keyed MERGEs make serialized
retries idempotent; they do not provide a database-enforced uniqueness
constraint or protect against concurrent ingestion writers.

Raw-document MERGE, chunk MERGE, and stale-chunk DELETE are independent Delta
transactions, not an atomic two-table batch. `DeltaPersistenceError` reports
acknowledged completed steps; after an ambiguous driver failure, retrying the
same plan is safe for serialized execution, but inspect/reconcile table state.
Spark SQL and Delta behavior have not been tested against a live workspace.

Official references:

- [Databricks constraints](https://docs.databricks.com/aws/en/tables/constraints)
- [Change data feed](https://docs.databricks.com/aws/en/tables/features/change-data-feed)
- [Create AI Search indexes](https://docs.databricks.com/aws/en/ai-search/create-ai-search)
- [Query foundation model serving endpoints](https://docs.databricks.com/aws/en/machine-learning/model-serving/score-foundation-models)

## Not verified

No live Databricks ingestion, Delta write, AI Search retrieval/index sync, or
model endpoint call has been performed. Workspace feature availability,
permissions, model choice, endpoint names, costs, and actual Spark SQL/Delta
semantics remain to be verified in the selected Free/DEV workspace.
