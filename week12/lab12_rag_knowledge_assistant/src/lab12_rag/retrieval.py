"""Small deterministic lexical retrieval interface for local development.

This module does not generate embeddings or perform semantic search. The
in-memory implementation ranks chunks by query-token overlap and is intended
for unit tests and local workflow development only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Protocol

from .chunking import DocumentChunk


_TOKEN = re.compile(r"[^\W_]+", flags=re.UNICODE)
_FILTERABLE_METADATA = frozenset({"doc_id", "source", "title", "url", "section"})


class Retriever(Protocol):
    """Interface implemented by local and future workspace retrievers."""

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Mapping[str, str | None] | None = None,
    ) -> list[DocumentChunk]:
        """Return matching chunks in descending relevance order."""


class InMemoryRetriever:
    """Rank a fixed collection by unique query-token overlap."""

    def __init__(self, chunks: Sequence[DocumentChunk]) -> None:
        self._chunks = tuple(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Mapping[str, str | None] | None = None,
    ) -> list[DocumentChunk]:
        if top_k < 0:
            raise ValueError("top_k must not be negative")
        filters = filters or {}
        unknown_filters = set(filters) - _FILTERABLE_METADATA
        if unknown_filters:
            names = ", ".join(sorted(unknown_filters))
            raise ValueError(f"Unsupported metadata filter(s): {names}")
        if top_k == 0:
            return []

        query_terms = _tokens(query)
        if not query_terms:
            return []

        ranked: list[tuple[int, int, DocumentChunk]] = []
        for position, chunk in enumerate(self._chunks):
            if any(getattr(chunk, field) != value for field, value in filters.items()):
                continue
            score = len(query_terms.intersection(_tokens(chunk.text)))
            if score:
                ranked.append((score, position, chunk))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [chunk for _, _, chunk in ranked[:top_k]]


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(text)}
