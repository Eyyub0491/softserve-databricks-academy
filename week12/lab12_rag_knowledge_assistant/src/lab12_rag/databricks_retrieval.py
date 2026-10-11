"""Databricks Vector Search adapter for managed-embedding Delta Sync indexes.

The index client is injected so importing this module does not authenticate,
connect to Databricks, or require the Databricks SDK. The client must expose the
``query_index`` method provided by ``WorkspaceClient.vector_search_indexes``.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any, Protocol

from .chunking import DocumentChunk
from .retrieval import _FILTERABLE_METADATA


_RESULT_COLUMNS = (
    "chunk_id",
    "doc_id",
    "source",
    "title",
    "url",
    "section",
    "chunk_index",
    "start_char",
    "end_char",
    "chunk_text",
)


class VectorSearchIndexClient(Protocol):
    """Subset of the installed Databricks SDK index-client interface."""

    def query_index(
        self,
        index_name: str,
        columns: list[str],
        *,
        filters_json: str | None = None,
        num_results: int | None = None,
        query_columns: list[str] | None = None,
        query_text: str | None = None,
        query_type: str | None = None,
    ) -> Any: ...


class DatabricksVectorSearchRetriever:
    """Query a managed-embedding Delta Sync index and map rows to chunks."""

    def __init__(self, index_client: VectorSearchIndexClient, index_name: str) -> None:
        if not index_name or len(index_name.split(".")) != 3:
            raise ValueError("index_name must be catalog.schema.index")
        self._index_client = index_client
        self._index_name = index_name

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Mapping[str, str | None] | None = None,
    ) -> list[DocumentChunk]:
        if top_k < 0:
            raise ValueError("top_k must not be negative")
        filter_values = dict(filters or {})
        unsupported = set(filter_values) - _FILTERABLE_METADATA
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise ValueError(f"Unsupported metadata filter(s): {names}")
        if any(not isinstance(value, str) for value in filter_values.values()):
            raise ValueError("Databricks Vector Search filters require string values")
        if top_k == 0 or not query.strip():
            return []

        response = self._index_client.query_index(
            index_name=self._index_name,
            columns=list(_RESULT_COLUMNS),
            query_text=query,
            query_columns=["chunk_text"],
            query_type="ANN",
            num_results=top_k,
            filters_json=json.dumps(filter_values) if filter_values else None,
        )
        return _map_results(response)


def _map_results(response: Any) -> list[DocumentChunk]:
    """Map the SDK response manifest and row arrays without reordering them."""
    manifest = getattr(response, "manifest", None)
    result = getattr(response, "result", None)
    columns = getattr(manifest, "columns", None)
    rows = getattr(result, "data_array", None)
    if not columns or rows is None:
        raise ValueError("Vector Search response is missing manifest columns or result rows")

    names = [getattr(column, "name", None) for column in columns]
    missing = set(_RESULT_COLUMNS) - set(names)
    if missing:
        raise ValueError("Vector Search response is missing column(s): " + ", ".join(sorted(missing)))

    positions = {name: names.index(name) for name in _RESULT_COLUMNS}
    chunks: list[DocumentChunk] = []
    for row_number, row in enumerate(rows):
        if len(row) != len(names):
            raise ValueError(f"Vector Search result row {row_number} has an unexpected column count")
        values = {name: row[position] for name, position in positions.items()}
        try:
            chunks.append(
                DocumentChunk(
                    chunk_id=_required_string(values, "chunk_id"),
                    doc_id=_required_string(values, "doc_id"),
                    source=_required_string(values, "source"),
                    title=_required_string(values, "title"),
                    url=_required_string(values, "url"),
                    section=_optional_string(values, "section"),
                    chunk_index=int(values["chunk_index"]),
                    start_char=int(values["start_char"]),
                    end_char=int(values["end_char"]),
                    text=_required_string(values, "chunk_text"),
                )
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Vector Search result row {row_number}: {exc}") from exc
    return chunks


def _required_string(values: Mapping[str, Any], field: str) -> str:
    value = values[field]
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _optional_string(values: Mapping[str, Any], field: str) -> str | None:
    value = values[field]
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{field} must be a string or null")
    return value
