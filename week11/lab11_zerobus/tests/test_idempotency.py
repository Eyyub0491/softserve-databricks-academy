import pytest

from src.events import make_event
from src.idempotency import deduplicate_events


def test_duplicate_events_collapse_to_one_logical_event():
    event = make_event(1)
    assert deduplicate_events([event, event]) == [event]


def test_distinct_events_remain_distinct_and_order_is_preserved():
    events = [make_event(2), make_event(3)]
    assert deduplicate_events(events) == events


def test_first_event_wins_if_same_id_has_conflicting_payload():
    first = make_event(1)
    conflicting = {**first, "payload": {"unexpected": True}}
    assert deduplicate_events([first, conflicting]) == [first]


def test_missing_event_id_is_rejected():
    with pytest.raises(ValueError, match="event_id"):
        deduplicate_events([{"event_type": "missing-id"}])
