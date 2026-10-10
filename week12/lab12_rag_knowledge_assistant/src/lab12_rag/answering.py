"""Generator-injected RAG and no-retrieval workflows.

The workflows associate answers with retrieved source metadata but do not
guarantee that a generator's response is factually supported by those sources.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from .chunking import DocumentChunk
from .retrieval import Retriever


NO_CONTEXT_ANSWER = "No matching source context was retrieved; no source-grounded answer was generated."


class AnswerGenerator(Protocol):
    """Interface for a fake local generator and a future LLM adapter."""

    def generate(self, query: str, context: Sequence[DocumentChunk]) -> str:
        """Generate text from a query and zero or more context chunks."""


@dataclass(frozen=True, slots=True)
class SourceReference:
    doc_id: str
    source: str
    title: str
    url: str
    section: str | None


@dataclass(frozen=True, slots=True)
class AnswerResult:
    answer: str
    source_references: tuple[SourceReference, ...]
    retrieved_chunk_ids: tuple[str, ...]
    mode: Literal["rag", "baseline"]
    context_available: bool


def answer_with_retrieval(
    query: str,
    retriever: Retriever,
    generator: AnswerGenerator,
    top_k: int = 5,
    filters: Mapping[str, str | None] | None = None,
) -> AnswerResult:
    """Retrieve context and pass it to a generator, or abstain if none matches."""
    chunks = retriever.search(query, top_k=top_k, filters=filters)
    if not chunks:
        return AnswerResult(
            answer=NO_CONTEXT_ANSWER,
            source_references=(),
            retrieved_chunk_ids=(),
            mode="rag",
            context_available=False,
        )

    answer = generator.generate(query, chunks)
    return AnswerResult(
        answer=answer,
        source_references=_source_references(chunks),
        retrieved_chunk_ids=tuple(chunk.chunk_id for chunk in chunks),
        mode="rag",
        context_available=True,
    )


def answer_without_retrieval(query: str, generator: AnswerGenerator) -> AnswerResult:
    """Run the same generator interface without document context or citations."""
    answer = generator.generate(query, ())
    return AnswerResult(
        answer=answer,
        source_references=(),
        retrieved_chunk_ids=(),
        mode="baseline",
        context_available=False,
    )


def _source_references(chunks: Sequence[DocumentChunk]) -> tuple[SourceReference, ...]:
    references: list[SourceReference] = []
    seen: set[tuple[str, str, str | None]] = set()
    for chunk in chunks:
        identity = (chunk.doc_id, chunk.url, chunk.section)
        if identity in seen:
            continue
        seen.add(identity)
        references.append(
            SourceReference(
                doc_id=chunk.doc_id,
                source=chunk.source,
                title=chunk.title,
                url=chunk.url,
                section=chunk.section,
            )
        )
    return tuple(references)
