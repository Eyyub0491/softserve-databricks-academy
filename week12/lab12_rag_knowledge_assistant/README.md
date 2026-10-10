# Lab 12 — RAG Knowledge Assistant

This project builds a local foundation for a Databricks knowledge assistant
over a small, explicitly allowlisted set of public Python documentation pages.
The local code includes configuration, document parsing, deterministic
chunking, lexical in-memory retrieval, and generator-injected answer workflows.
The offline unit tests do not fetch documents, connect to Databricks, create
embeddings, or call AI Search or an LLM. Invoking
`DatabricksVectorSearchRetriever.search()` with a real index client does make
an AI Search query.

## Local setup

Use Python 3.10 or newer. From this directory:

```powershell
python -m pip install -r requirements.txt
python -m pytest -p no:cacheprovider tests/unit -q
```

The tests use local fixtures and fake components; they do not require network
access or Databricks credentials.

## Intended architecture

1. Fetch allowlisted Python documentation pages and parse normalized text with
   title, URL, source, and section metadata.
2. Store raw documents and deterministic chunks in Unity Catalog Delta tables.
3. Create a Databricks AI Search (formerly Vector Search) index over chunks.
4. Replace the local lexical retriever with workspace retrieval using top-k and
   metadata filters.
5. Connect an approved LLM adapter, compare RAG answers with a no-retrieval
   baseline, and add privacy-aware evaluation logging.

The current `InMemoryRetriever` ranks by query-token overlap; it is not semantic
search and does not use embeddings. `DatabricksVectorSearchRetriever` is an
injected-client adapter for managed-embedding Delta Sync indexes. It issues
ANN text queries through the locally inspected `WorkspaceClient.vector_search_indexes.query_index`
API and maps returned rows to `DocumentChunk`. The adapter does not create an
authenticated client. The installed local environment exposes that SDK API,
but the SDK is not declared in `requirements.txt`; no workspace query or
service integration has been tested. If it retrieves no matching chunk, the RAG
workflow abstains without calling its answer generator. With context, source
references identify retrieved document metadata; they do not prove that the
generated answer is factually supported. The baseline calls the same generator
with no context and returns no source references.

`sql/create_tables.sql` contains proposed raw-document and chunk table schemas.
Replace its catalog/schema placeholders only after a workspace target and
permissions are explicitly selected. The SQL is not executed by local tests.

`ingestion.py` prepares rows without writing them, and `reconciliation.py`
plans row upserts and stale-chunk deletions. `delta_writer.py` applies a plan
through an injected Spark session to existing Delta tables; it does not create
tables or a Spark session. The writer validates fully qualified table names and
row shapes, merges by `doc_id` and `chunk_id`, and timestamps `ingested_at`
inside the raw-table MERGE. The Spark/Delta APIs are supplied by a Databricks
runtime and are not project dependencies. Writer tests use a fake Spark SQL
interface; actual Spark SQL parsing and Delta behavior have not been verified
against a workspace.

Each raw-table MERGE, chunk-table MERGE, and stale-chunk DELETE is a separate
Delta transaction; the two tables are not atomic as one operation. On failure,
`DeltaPersistenceError` reports the acknowledged completed steps. Retry the
same plan: keyed MERGEs avoid duplicate rows, unchanged rows retain their
persisted timestamps, and repeating a scoped DELETE is a no-op. If a driver
loses the response after a statement committed, completion may be uncertain;
retrying the same plan is still safe, but a run-level completion record or
post-write reconciliation is needed to confirm the overall batch.

Configure `LAB12_VECTOR_SEARCH_INDEX_NAME` as a three-part index identifier and
`LAB12_RETRIEVAL_TOP_K` for the retrieval limit when wiring the adapter. These
settings contain no credentials. Workspace catalog/schema names, AI Search
availability, embedding and LLM endpoints, required permissions, and costs are
not configured or verified here. Integration dependencies and workspace tests
remain separate from the offline unit suite.
