"""Refresh FX rate snapshots from fxratesapi.com every 5 minutes."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine

from airflow import DAG

sys.path.insert(0, "/opt/airflow")

logger = logging.getLogger(__name__)

FRAUD_DB_URL = os.getenv(
    "FRAUD_DATABASE_URL",
    "postgresql+psycopg2://fraud:fraud@postgres:5432/fraud_db",
)


def refresh_fx_rates(**_context):
    from shared.fx_client import fetch_latest_rates, persist_snapshot

    api_key = os.getenv("FX_API_KEY", "")
    if not api_key:
        raise ValueError("FX_API_KEY environment variable is not set")

    rates, as_of = fetch_latest_rates(api_key)
    engine = create_engine(FRAUD_DB_URL, pool_pre_ping=True)
    snapshot_id = persist_snapshot(engine, rates, as_of)
    logger.info("FX snapshot persisted: id=%s as_of=%s", snapshot_id, as_of.isoformat())
    return {"snapshot_id": snapshot_id, "as_of": as_of.isoformat()}


default_args = {
    "owner": "fraud-detection",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="fx_rate_refresh",
    default_args=default_args,
    description="Fetch FX rates from fxratesapi.com and store in Postgres",
    schedule_interval="*/5 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["fx", "fraud"],
) as dag:
    PythonOperator(
        task_id="refresh_fx_rates",
        python_callable=refresh_fx_rates,
    )
