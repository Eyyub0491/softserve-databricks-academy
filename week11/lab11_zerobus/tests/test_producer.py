from unittest.mock import Mock

from src.config import ZerobusConfig
from src.events import make_event
from src.producer import send_events


def _config():
    from unittest.mock import Mock

    dbutils = Mock()
    dbutils.secrets.get.return_value = "test-secret"
    return ZerobusConfig.from_env({}, dbutils=dbutils)


def test_producer_uses_mock_sdk_flushes_and_closes_without_network():
    stream = Mock()
    sdk = Mock()
    sdk.create_stream.return_value = stream
    sdk_factory = Mock(return_value=sdk)
    table_properties = Mock(side_effect=lambda table: ("table", table))
    events = [make_event(0), make_event(1)]

    assert send_events(_config(), events, sdk_factory, table_properties) == 2

    sdk_factory.assert_called_once_with(_config().endpoint, _config().host)
    sdk.create_stream.assert_called_once_with(
        "b1d1c4a6-655a-4448-b178-67637b40951e",
        "test-secret",
        ("table", "lab5.default.lab11_events"),
    )
    assert stream.ingest_record_offset.call_count == 2
    stream.flush.assert_called_once_with()
    stream.close.assert_called_once_with()


def test_producer_closes_stream_when_ingest_fails():
    stream = Mock()
    stream.ingest_record_offset.side_effect = RuntimeError("send failed")
    sdk = Mock()
    sdk.create_stream.return_value = stream

    try:
        send_events(_config(), [make_event(0)], lambda *_: sdk, lambda table: table)
    except RuntimeError as exc:
        assert str(exc) == "send failed"
    else:
        raise AssertionError("expected send failure")
    stream.close.assert_called_once_with()
