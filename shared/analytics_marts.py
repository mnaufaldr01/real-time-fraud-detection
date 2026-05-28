"""Shared helpers for loading dbt analytics marts from Postgres."""

from __future__ import annotations

import json
import os
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fraud:fraud@localhost:5433/fraud_db")
AUTO_REFRESH_SECONDS = int(os.getenv("DASHBOARD_AUTO_REFRESH_SECONDS", "60"))

GENERAL_TREND_MARTS = {
    "Yearly": "mart_fraud_trend_yearly",
    "Monthly": "mart_fraud_trend_monthly",
    "Daily": "mart_fraud_trend_daily",
}

VELOCITY_TREND_MARTS = {
    "Yearly": "mart_velocity_trend_yearly",
    "Monthly": "mart_velocity_trend_monthly",
    "Daily": "mart_velocity_trend_daily",
}

VELOCITY_SHARE_TREND_MARTS = {
    "Yearly": "mart_velocity_share_trend_yearly",
    "Monthly": "mart_velocity_share_trend_monthly",
    "Daily": "mart_velocity_share_trend",
}

Granularity = str


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def load_mart(table: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(f"SELECT * FROM analytics.{table}"), conn)


def load_trend(mart_map: dict[str, str], granularity: str) -> pd.DataFrame:
    table = mart_map.get(granularity, mart_map["Daily"])
    return load_mart(table)


def mart_exists(table: str) -> bool:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'analytics'
                      AND table_name = :table
                )
                """
            ),
            {"table": table},
        ).scalar()
    return bool(row)


def get_marts_fingerprint() -> str | None:
    """Lightweight signature of KPI marts; changes when Airflow/local dbt rebuilds data."""
    if not mart_exists("mart_general_kpis"):
        return None
    engine = get_engine()
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT concat_ws(
                    '|',
                    total_tx::text,
                    flagged_count::text,
                    fraud_count::text,
                    fraud_rate_pct::text,
                    review_queue_count::text,
                    review_share_of_actions_pct::text
                )
                FROM analytics.mart_general_kpis
                """
            )
        ).scalar()


def df_to_records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


def df_first_row(df: pd.DataFrame) -> dict | None:
    records = df_to_records(df)
    return records[0] if records else None
