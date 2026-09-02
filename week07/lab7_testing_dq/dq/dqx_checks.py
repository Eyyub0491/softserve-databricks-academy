from __future__ import annotations

import os
from typing import Any

from databricks.labs.dqx.check_funcs import foreign_key, is_in_range, is_not_null, is_unique
from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.rule import DQDatasetRule, DQRowRule
from databricks.sdk import WorkspaceClient
from pyspark.sql import DataFrame, SparkSession


def build_customer_dqx_rules() -> list[Any]:
    """Return DQX rules for the silver customer table."""
    return [
        DQRowRule(
            check_func=is_not_null,
            column="customer_id",
            name="customer_id_not_null",
            criticality="error",
        ),
        DQRowRule(
            check_func=is_not_null,
            column="state",
            name="state_not_null",
            criticality="error",
        ),
        DQRowRule(
            check_func=is_in_range,
            column="loyalty_segment",
            check_func_kwargs={"min_limit": 0, "max_limit": 3},
            name="loyalty_segment_in_range",
            criticality="error",
        ),
        DQDatasetRule(
            check_func=is_unique,
            columns=["customer_id"],
            name="customer_id_is_unique",
            criticality="error",
        ),
    ]


def build_fact_reference_dqx_rules() -> list[Any]:
    """Return a DQX rule set for the gold fact table foreign-key checks."""
    return [
        DQDatasetRule(
            check_func=foreign_key,
            columns=["customer_key"],
            check_func_kwargs={"ref_columns": ["customer_key"], "ref_df_name": "dim_customers"},
            name="fct_customer_key_exists",
            criticality="error",
        ),
        DQDatasetRule(
            check_func=foreign_key,
            columns=["product_key"],
            check_func_kwargs={"ref_columns": ["product_key"], "ref_df_name": "dim_products"},
            name="fct_product_key_exists",
            criticality="error",
        ),
        DQDatasetRule(
            check_func=foreign_key,
            columns=["date_key"],
            check_func_kwargs={"ref_columns": ["date_key"], "ref_df_name": "dim_date"},
            name="fct_date_key_exists",
            criticality="error",
        ),
    ]


def _build_engine(
    spark: SparkSession,
    workspace_client: WorkspaceClient | None = None,
) -> DQEngine:
    return DQEngine(
        workspace_client=workspace_client or WorkspaceClient(
            profile=os.environ.get("DATABRICKS_PROFILE", os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT"))
        ),
        spark=spark,
    )


def run_dqx_customer_validation(
    spark: SparkSession,
    customer_df: DataFrame,
    workspace_client: WorkspaceClient | None = None,
) -> tuple[DataFrame, DataFrame]:
    """Apply DQX checks to the silver customer table and split valid vs failing rows."""
    engine = _build_engine(spark, workspace_client)
    result = engine.apply_checks_and_split(customer_df, build_customer_dqx_rules())
    if len(result) == 3:
        valid_df, invalid_df, _ = result
    else:
        valid_df, invalid_df = result
    return valid_df, invalid_df


def run_dqx_fact_reference_validation(
    spark: SparkSession,
    fact_df: DataFrame,
    ref_dfs: dict[str, DataFrame],
    workspace_client: WorkspaceClient | None = None,
) -> tuple[DataFrame, DataFrame]:
    """Apply DQX foreign-key checks against the fact table and the reference dimensions."""
    engine = _build_engine(spark, workspace_client)
    result = engine.apply_checks_and_split(fact_df, build_fact_reference_dqx_rules(), ref_dfs)
    if len(result) == 3:
        valid_df, invalid_df, _ = result
    else:
        valid_df, invalid_df = result
    return valid_df, invalid_df
