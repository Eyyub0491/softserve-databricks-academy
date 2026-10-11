"""Side-by-side evaluation of retrieval-augmented and baseline answers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .answering import AnswerGenerator, AnswerResult, answer_with_retrieval, answer_without_retrieval
from .retrieval import Retriever


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    query: str


@dataclass(frozen=True, slots=True)
class EvaluationComparison:
    case: EvaluationCase
    rag: AnswerResult
    baseline: AnswerResult


def compare_rag_with_baseline(
    cases: Sequence[EvaluationCase],
    retriever: Retriever,
    generator: AnswerGenerator,
    *,
    top_k: int = 5,
) -> tuple[EvaluationComparison, ...]:
    """Run each fixed query through RAG and baseline workflows in input order."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    seen_ids: set[str] = set()
    comparisons: list[EvaluationComparison] = []
    for case in cases:
        if not case.case_id.strip():
            raise ValueError("Evaluation case IDs must not be empty")
        if case.case_id in seen_ids:
            raise ValueError(f"Duplicate evaluation case ID: {case.case_id}")
        if not case.query.strip():
            raise ValueError(f"Evaluation query must not be empty: {case.case_id}")
        seen_ids.add(case.case_id)
        comparisons.append(
            EvaluationComparison(
                case=case,
                rag=answer_with_retrieval(case.query, retriever, generator, top_k=top_k),
                baseline=answer_without_retrieval(case.query, generator),
            )
        )
    return tuple(comparisons)
