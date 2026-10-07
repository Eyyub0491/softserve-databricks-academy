"""Deterministic sample events for repeatable ingestion demonstrations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5


_EVENT_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_event(sequence: int, producer_id: str = "lab11-demo-producer") -> dict[str, Any]:
    """Create a repeatable event; repeating producer and sequence repeats its ID."""
    if sequence < 0:
        raise ValueError("sequence must be zero or greater")
    event_id = str(uuid5(NAMESPACE_URL, f"softserve-lab11:{producer_id}:{sequence}"))
    event_time = (_EVENT_EPOCH + timedelta(seconds=sequence)).isoformat().replace("+00:00", "Z")
    return {
        "event_id": event_id,
        "event_type": "order.created",
        "event_time": event_time,
        "producer_id": producer_id,
        "payload": {"order_id": f"order-{sequence:04d}", "amount": 42.50 + sequence},
    }


def generate_events(count: int, producer_id: str = "lab11-demo-producer", start: int = 0) -> list[dict[str, Any]]:
    if count < 0:
        raise ValueError("count must be zero or greater")
    return [make_event(i, producer_id) for i in range(start, start + count)]


def to_zerobus_record(event: dict[str, Any]) -> dict[str, Any]:
    """Map the Python event into the SQL table shape (payload is JSON text)."""
    return {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "event_time": event["event_time"],
        "producer_id": event["producer_id"],
        "payload": json.dumps(event["payload"], sort_keys=True, separators=(",", ":")),
    }
