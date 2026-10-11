"""Explicit runtime entry points for Lab 12 setup, ingestion, and queries."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .answering import AnswerResult, answer_with_retrieval
from .chat_model import DatabricksServingChatModel
from .config import Lab12Config
from .databricks_retrieval import DatabricksVectorSearchRetriever
from .documents import DocumentRecord, fetch_document_html, parse_document
from .evaluation import EvaluationCase, EvaluationComparison, compare_rag_with_baseline
from .ingestion import PreparedIngestion, prepare_ingestion
from .reconciliation import ReconciliationPlan, plan_reconciliation
from .retrieval import Retriever
from .delta_writer import DeltaTableWriter, DeltaWriteResult


_RAW_COMPARE_COLUMNS = (
    "doc_id", "source", "title", "url", "content", "content_sha256",
)
_CHUNK_COMPARE_COLUMNS = (
    "chunk_id", "doc_id", "source", "title", "url", "section",
    "chunk_index", "start_char", "end_char", "chunk_text", "chunk_sha256",
)


@dataclass(frozen=True, slots=True)
class IngestionRun:
    prepared: PreparedIngestion
    plan: ReconciliationPlan
    persistence: DeltaWriteResult


@dataclass(frozen=True, slots=True)
class Lab12Runtime:
    config: Lab12Config
    retriever: Retriever
    generator: DatabricksServingChatModel

    def answer(self, query: str) -> AnswerResult:
        return answer_with_retrieval(
            query,
            self.retriever,
            self.generator,
            top_k=self.config.retrieval_top_k,
        )

    def evaluate(
        self,
        cases: Sequence[EvaluationCase],
    ) -> tuple[EvaluationComparison, ...]:
        return compare_rag_with_baseline(
            cases,
            self.retriever,
            self.generator,
            top_k=self.config.retrieval_top_k,
        )

FetchHTML = Callable[[str], str]
ParseDocument = Callable[[str, str], DocumentRecord]
Clock = Callable[[], datetime]


def create_runtime(
    config: Lab12Config | None = None,
    *,
    workspace_client: Any | None = None,
) -> Lab12Runtime:
    """Build query adapters; default SDK authentication uses its normal auth chain."""
    settings = config or Lab12Config.from_env()
    index_name, endpoint_name = settings.require_query_targets()
    if workspace_client is None:
        from databricks.sdk import WorkspaceClient

        workspace_client = WorkspaceClient()
    return Lab12Runtime(
        config=settings,
        retriever=DatabricksVectorSearchRetriever(
            workspace_client.vector_search_indexes,
            index_name,
        ),
        generator=DatabricksServingChatModel(
            workspace_client.serving_endpoints_data_plane,
            endpoint_name,
            max_tokens=settings.chat_max_tokens,
        ),
    )


def run_ingestion(
    spark: Any,
    config: Lab12Config | None = None,
    *,
    fetch_html: FetchHTML = fetch_document_html,
    parse: ParseDocument = parse_document,
    clock: Clock | None = None,
) -> IngestionRun:
    """Fetch the allowlist, plan reconciliation, and persist to existing tables.

    This explicit operation performs public-document network requests and Delta
    writes. It does not create tables or synchronize an AI Search index.
    """
    settings = config or Lab12Config.from_env()
    catalog, schema = settings.require_workspace_target()
    raw_table = f"{catalog}.{schema}.raw_documents"
    chunks_table = f"{catalog}.{schema}.document_chunks"
    prepared = prepare_ingestion(
        config=settings,
        fetch_html=fetch_html,
        parse=parse,
        clock=clock,
    )
    existing_documents = _read_rows(spark, raw_table, _RAW_COMPARE_COLUMNS)
    existing_chunks = _read_rows(spark, chunks_table, _CHUNK_COMPARE_COLUMNS)
    plan = plan_reconciliation(
        prepared,
        existing_document_rows=existing_documents,
        existing_chunk_rows=existing_chunks,
    )
    persistence = DeltaTableWriter(spark, raw_table, chunks_table).persist(plan)
    return IngestionRun(prepared, plan, persistence)


def _read_rows(spark: Any, table_name: str, columns: Sequence[str]) -> list[Mapping[str, object]]:
    return [
        row.asDict(recursive=True)
        for row in spark.table(table_name).select(*columns).collect()
    ]
