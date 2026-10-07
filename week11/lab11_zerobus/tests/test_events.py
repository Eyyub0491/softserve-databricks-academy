from src.events import generate_events, make_event, to_zerobus_record


def test_event_generation_has_expected_schema_and_deterministic_id():
    first = make_event(3)
    assert first == make_event(3)
    assert set(first) == {"event_id", "event_type", "event_time", "producer_id", "payload"}
    assert first["event_id"] != make_event(4)["event_id"]
    assert first["event_time"].endswith("Z")


def test_generation_can_repeat_a_selected_event_for_replay():
    assert generate_events(1, start=7)[0] == generate_events(1, start=7)[0]


def test_zerobus_record_serializes_payload_to_string():
    record = to_zerobus_record(make_event(0))
    assert isinstance(record["payload"], str)
    assert '"order_id":"order-0000"' in record["payload"]
