"""Small pure-Python model of event-key deduplication for local tests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def deduplicate_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep the first occurrence of each event_id, preserving input order.

    Raw ingestion remains append-oriented. This helper models the curated
    processing rule; it does not make Zerobus delivery itself idempotent.
    """
    unique: dict[str, dict[str, Any]] = {}
    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("each event must have a non-empty event_id")
        unique.setdefault(event_id, dict(event))
    return list(unique.values())
