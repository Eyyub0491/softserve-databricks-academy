"""Lab 11 — Zerobus producer.

Pushes events directly into a Unity Catalog Delta table via the
Databricks Zerobus Ingest SDK, with no message-bus layer in between.

Usage (from a Databricks notebook)::

    from producer import run_producer
    run_producer(dbutils=dbutils, count=5, start=0)

Credentials are read at runtime from Databricks Secrets — never
hard-coded.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SECRET_SCOPE = "lab11_zerobus"
CLIENT_ID_KEY = "client_id"
CLIENT_SECRET_KEY = "client_secret"

WORKSPACE_URL = "https://dbc-f7231d90-d8a3.cloud.databricks.com"
WORKSPACE_ID = "7474657415962864"
ZEROBUS_HOST = f"{WORKSPACE_ID}.zerobus.us-east-2.cloud.databricks.com"

TABLE_NAME = "lab5.default.lab11_events"

EVENT_TYPES = [
    "order_created",
    "user_signup",
    "payment_processed",
    "inventory_updated",
    "notification_sent",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_event(index: int) -> Dict[str, Any]:
    """Build a single event dict matching the table schema."""
    event_id = f"evt_{index:04d}"
    event_type = EVENT_TYPES[index % len(EVENT_TYPES)]
    # Zerobus expects TIMESTAMP as int64 epoch microseconds (not a string)
    event_time = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    producer_id = "lab11-zerobus-producer"
    payload = json.dumps({
        "source": "lab11",
        "sequence": index,
        "metadata": {"env": "free", "region": "us-east-2"},
    })
    return {
        "event_id": event_id,
        "event_type": event_type,
        "event_time": event_time,
        "producer_id": producer_id,
        "payload": payload,
    }


def _get_credentials(dbutils) -> tuple[str, str]:
    """Read OAuth client_id and client_secret from Databricks Secrets."""
    client_id = dbutils.secrets.get(scope=SECRET_SCOPE, key=CLIENT_ID_KEY)
    client_secret = dbutils.secrets.get(scope=SECRET_SCOPE, key=CLIENT_SECRET_KEY)
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing credentials: ensure scope 'lab11_zerobus' has "
            "keys 'client_id' and 'client_secret'."
        )
    return client_id, client_secret


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def run_producer(
    dbutils,
    count: int = 5,
    start: int = 0,
) -> Dict[str, Any]:
    """Push *count* events (numbered from *start*) into the Zerobus target table.

    Returns a dict with ``submitted``, ``acknowledged``, ``events``, and
    ``duration_s`` keys.
    """
    t0 = time.monotonic()

    import zerobus  # lazy import — allows local tests without the SDK installed

    client_id, client_secret = _get_credentials(dbutils)
    logger.info("Credentials loaded from Databricks Secrets.")

    sdk = zerobus.ZerobusSdk(
        host=ZEROBUS_HOST,
        unity_catalog_url=WORKSPACE_URL,
        application_name="lab11-zerobus-producer",
    )
    logger.info("ZerobusSdk initialised  host=%s", ZEROBUS_HOST)

    table_props = zerobus.TableProperties(table_name=TABLE_NAME)
    logger.info("TableProperties  table=%s  record_format=%s",
               table_props.table_name, table_props.record_format)

    stream = sdk.create_stream(
        client_id=client_id,
        client_secret=client_secret,
        table_properties=table_props,
    )
    logger.info("Stream created for %s", TABLE_NAME)

    events: list[Dict[str, Any]] = []
    last_offset: Optional[int] = None

    try:
        for i in range(start, start + count):
            event = _make_event(i)
            events.append(event)
            payload_json = json.dumps(event)
            offset = stream.ingest_record_offset(payload_json)
            last_offset = offset
            logger.info("Ingested  event_id=%s  offset=%s", event["event_id"], offset)

        # Wait for all records to be acknowledged
        if last_offset is not None:
            stream.wait_for_offset(last_offset)
            logger.info("All records acknowledged up to offset=%s", last_offset)

        stream.flush()

    finally:
        stream.close()

    elapsed = round(time.monotonic() - t0, 2)
    result = {
        "submitted": count,
        "acknowledged": count,
        "events": events,
        "duration_s": elapsed,
        "table": TABLE_NAME,
        "last_offset": last_offset,
    }
    logger.info("run_producer done  submitted=%d  acknowledged=%d  duration=%.2fs",
               count, count, elapsed)
    return result