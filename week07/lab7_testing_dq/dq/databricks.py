"""Lightweight Databricks query helpers for the Lab 7 integration tests.

This uses the supported Databricks SQL connector with the existing CLI profile
(DEFAULT), avoiding Databricks Connect and the unsupported SQL Statements REST
path that is not available in the free workspace.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Optional

from databricks import sql
from databricks.sdk.core import Config


DEFAULT_PROFILE = "DEFAULT"


def run_cli_command(command: list[str]) -> Any:
    """Run a Databricks CLI command and return parsed JSON when possible."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Databricks CLI command failed: {' '.join(command)}\n{stderr}")

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return stdout


def resolve_warehouse_id(profile: str = DEFAULT_PROFILE) -> str:
    """Resolve a warehouse id from the existing CLI profile."""
    payload = run_cli_command([
        "databricks",
        "warehouses",
        "list",
        "--profile",
        profile,
        "--output",
        "json",
    ])

    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected warehouse-list response: {payload!r}")

    for warehouse in payload:
        if warehouse.get("state") == "RUNNING":
            return warehouse["id"]

    if payload:
        return payload[0]["id"]

    raise RuntimeError(f"No Databricks warehouse found for profile '{profile}'.")


def execute_sql(
    query: str,
    profile: str = DEFAULT_PROFILE,
    warehouse_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Execute a query using the Databricks SQL connector and the DEFAULT profile."""
    config = Config(profile=profile)
    if not config.host or not config.token:
        raise RuntimeError(f"No Databricks authentication is available for profile '{profile}'.")

    if warehouse_id is None:
        warehouse_id = resolve_warehouse_id(profile)

    server_hostname = config.host.replace("https://", "").replace("http://", "")
    http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    connection = sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=config.token,
    )

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        columns = [field[0] for field in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        connection.close()
