"""Environment and Databricks-secret configuration for the Zerobus producer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Mapping


DEFAULT_HOST = "https://dbc-f7231d90-d8a3.cloud.databricks.com"
DEFAULT_WORKSPACE_ID = "7474657415962864"
DEFAULT_CLIENT_ID = "b1d1c4a6-655a-4448-b178-67637b40951e"
DEFAULT_CATALOG = "lab5"
DEFAULT_SCHEMA = "default"
DEFAULT_TABLE = "lab11_events"
DEFAULT_SECRET_SCOPE = "lab11_zerobus"
DEFAULT_SECRET_KEY = "client_secret"


@dataclass(frozen=True)
class ZerobusConfig:
    host: str
    workspace_id: str
    endpoint: str
    client_id: str
    client_secret: str = field(repr=False)
    catalog: str
    schema: str
    table: str

    @property
    def table_name(self) -> str:
        return f"{self.catalog}.{self.schema}.{self.table}"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, dbutils: Any = None) -> "ZerobusConfig":
        """Read public settings from env and the OAuth secret from Databricks Secrets.

        The secret is deliberately never read from an environment variable or a
        dotenv file. Local tests can pass a small fake ``dbutils`` object.
        """
        values = os.environ if env is None else env
        host = values.get("DATABRICKS_HOST", DEFAULT_HOST).strip().rstrip("/")
        workspace_id = values.get("DATABRICKS_WORKSPACE_ID", DEFAULT_WORKSPACE_ID).strip()
        client_id = values.get("ZEROBUS_CLIENT_ID", DEFAULT_CLIENT_ID).strip()
        if not workspace_id:
            raise ValueError("DATABRICKS_WORKSPACE_ID must not be empty")
        if dbutils is None:
            raise ValueError(
                "Databricks dbutils is required to read the Zerobus client secret "
                f"from scope '{DEFAULT_SECRET_SCOPE}', key '{DEFAULT_SECRET_KEY}'. "
                "Call run_producer(dbutils=dbutils) from a Databricks notebook."
            )
        try:
            client_secret = dbutils.secrets.get(
                scope=DEFAULT_SECRET_SCOPE,
                key=DEFAULT_SECRET_KEY,
            )
        except Exception:
            raise ValueError(
                "Could not read the Zerobus client secret from the configured Databricks secret scope/key"
            ) from None
        if not isinstance(client_secret, str) or not client_secret:
            raise ValueError("Databricks returned an empty Zerobus client secret")
        if not client_id:
            raise ValueError("ZEROBUS_CLIENT_ID must not be empty")
        endpoint = values.get("ZEROBUS_ENDPOINT", "").strip().rstrip("/")
        if not endpoint:
            endpoint = f"https://{workspace_id}.zerobus.us-east-2.cloud.databricks.com"
        elif not endpoint.startswith(("https://", "http://")):
            endpoint = "https://" + endpoint
        return cls(
            host=host,
            workspace_id=workspace_id,
            endpoint=endpoint,
            client_id=client_id,
            client_secret=client_secret,
            catalog=values.get("ZEROBUS_CATALOG", DEFAULT_CATALOG).strip(),
            schema=values.get("ZEROBUS_SCHEMA", DEFAULT_SCHEMA).strip(),
            table=values.get("ZEROBUS_TABLE", DEFAULT_TABLE).strip(),
        )
