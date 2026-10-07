"""Send deterministic JSON events directly to a Unity Catalog table."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Callable

from .config import ZerobusConfig
from .events import generate_events, to_zerobus_record


SdkFactory = Callable[[str, str], Any]
TablePropertiesFactory = Callable[[str], Any]


def _default_sdk_factory(endpoint: str, host: str) -> Any:
    # Import lazily so local tests and event helpers need no SDK/network setup.
    from zerobus.sdk.sync import ZerobusSdk

    return ZerobusSdk(endpoint, host, application_name="softserve-lab11/1.0")


def send_events(
    config: ZerobusConfig,
    events: Iterable[Mapping[str, Any]],
    sdk_factory: SdkFactory | None = None,
    table_properties_factory: TablePropertiesFactory | None = None,
) -> int:
    """Queue events, flush for durable acknowledgment, and always close stream."""
    if table_properties_factory is None:
        from zerobus.sdk.shared import TableProperties

        table_properties_factory = TableProperties
    sdk = (sdk_factory or _default_sdk_factory)(config.endpoint, config.host)
    stream = sdk.create_stream(
        config.client_id,
        config.client_secret,
        table_properties_factory(config.table_name),  # no descriptor selects JSON mode
    )
    sent = 0
    try:
        for event in events:
            stream.ingest_record_offset(to_zerobus_record(dict(event)))
            sent += 1
        # flush() confirms all queued records have been acknowledged.
        stream.flush()
        return sent
    finally:
        stream.close()


def run_producer(
    dbutils: Any,
    count: int = 5,
    start: int = 0,
    producer_id: str = "lab11-demo-producer",
) -> int:
    """Notebook-safe entry point; accepts Databricks' notebook ``dbutils``."""
    if count < 0 or start < 0:
        raise ValueError("count and start must be zero or greater")
    config = ZerobusConfig.from_env(dbutils=dbutils)
    events = generate_events(count, producer_id, start)
    sent = send_events(config, events)
    print(f"Acknowledged {sent} event(s) for {config.table_name}")
    return sent


def main(
    dbutils: Any = None,
    count: int = 5,
    start: int = 0,
    producer_id: str = "lab11-demo-producer",
) -> int:
    """Compatibility entry point; Databricks notebooks pass their ``dbutils``."""
    return run_producer(dbutils, count=count, start=start, producer_id=producer_id)


if __name__ == "__main__":
    raise SystemExit(main())
