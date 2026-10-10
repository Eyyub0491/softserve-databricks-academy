from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import src.lab12_rag.runtime as runtime_module
from src.lab12_rag.config import Lab12Config
from src.lab12_rag.documents import ALLOWED_DOCUMENTS
from src.lab12_rag.evaluation import EvaluationCase
from src.lab12_rag.ingestion import PreparedIngestion
from src.lab12_rag.runtime import create_runtime, run_ingestion


class FakeWorkspaceClient:
    def __init__(self):
        self.vector_search_indexes = object()
        self.serving_endpoints_data_plane = object()


def test_create_runtime_wires_sdk_services_with_explicit_settings(monkeypatch):
    observed = {}

    class FakeRetriever:
        def __init__(self, client, index_name):
            observed["index"] = (client, index_name)

    class FakeModel:
        def __init__(self, client, endpoint_name, *, max_tokens):
            observed["model"] = (client, endpoint_name, max_tokens)

    monkeypatch.setattr(runtime_module, "DatabricksVectorSearchRetriever", FakeRetriever)
    monkeypatch.setattr(runtime_module, "DatabricksServingChatModel", FakeModel)
    client = FakeWorkspaceClient()
    config = Lab12Config(
        vector_search_index_name="training.lab12.chunks",
        chat_serving_endpoint_name="lab12-chat",
        chat_max_tokens=256,
    )

    runtime = create_runtime(config, workspace_client=client)

    assert runtime.config is config
    assert observed["index"] == (client.vector_search_indexes, "training.lab12.chunks")
    assert observed["model"] == (client.serving_endpoints_data_plane, "lab12-chat", 256)


class FakeSparkRows:
    def __init__(self, rows, calls):
        self.rows = rows
        self.calls = calls

    def select(self, *columns):
        self.calls.append(("select", columns))
        return self

    def collect(self):
        return self.rows


class FakeSpark:
    def __init__(self):
        self.calls = []

    def table(self, name):
        self.calls.append(("table", name))
        return FakeSparkRows([], self.calls)


def test_run_ingestion_reads_existing_tables_plans_then_persists(monkeypatch):
    prepared = PreparedIngestion((), (), ())
    observed = {}

    def prepare(**kwargs):
        observed["prepare"] = kwargs
        return prepared

    class FakeWriter:
        def __init__(self, spark, raw_table, chunks_table):
            observed["writer"] = (spark, raw_table, chunks_table)

        def persist(self, plan):
            observed["plan"] = plan
            return SimpleNamespace(completed_steps=())

    monkeypatch.setattr(runtime_module, "prepare_ingestion", prepare)
    monkeypatch.setattr(runtime_module, "DeltaTableWriter", FakeWriter)
    spark = FakeSpark()
    config = Lab12Config(catalog="training", schema="lab12")

    result = run_ingestion(spark, config)

    assert result.prepared is prepared
    assert result.persistence.completed_steps == ()
    assert observed["writer"] == (
        spark,
        "training.lab12.raw_documents",
        "training.lab12.document_chunks",
    )
    assert observed["plan"].failed_urls == ()
    assert [call[1] for call in spark.calls if call[0] == "table"] == [
        "training.lab12.raw_documents",
        "training.lab12.document_chunks",
    ]


def test_run_ingestion_can_prepare_allowlisted_rows_without_live_fetch(monkeypatch):
    timestamp = datetime(2026, 4, 1, tzinfo=timezone.utc)
    html = "<html><body><h1>Examples</h1><p>offline fixture text</p></body></html>"
    fetched = []

    class FakeWriter:
        def __init__(self, *_args):
            pass

        def persist(self, plan):
            return SimpleNamespace(completed_steps=())

    monkeypatch.setattr(runtime_module, "DeltaTableWriter", FakeWriter)
    result = run_ingestion(
        FakeSpark(),
        Lab12Config(catalog="training", schema="lab12", chunk_size=100, chunk_overlap=10),
        fetch_html=lambda url: fetched.append(url) or html,
        clock=lambda: timestamp,
    )

    assert fetched == [source.url for source in ALLOWED_DOCUMENTS]
    assert len(result.prepared.document_rows) == len(ALLOWED_DOCUMENTS)
    assert len(result.prepared.chunk_rows) == len(ALLOWED_DOCUMENTS)
    assert result.plan.failed_urls == ()


def test_create_runtime_fails_before_client_creation_when_settings_are_missing():
    with pytest.raises(ValueError, match="LAB12_VECTOR_SEARCH_INDEX_NAME"):
        create_runtime(Lab12Config())


def test_runtime_evaluation_uses_configured_retrieval_limit(monkeypatch):
    calls = {}

    def compare(cases, retriever, generator, *, top_k):
        calls["values"] = (cases, retriever, generator, top_k)
        return ()

    monkeypatch.setattr(runtime_module, "compare_rag_with_baseline", compare)
    retriever, generator = object(), object()
    runtime = runtime_module.Lab12Runtime(
        Lab12Config(retrieval_top_k=7),
        retriever,
        generator,
    )
    cases = (EvaluationCase("case-1", "question"),)

    assert runtime.evaluate(cases) == ()
    assert calls["values"] == (cases, retriever, generator, 7)
