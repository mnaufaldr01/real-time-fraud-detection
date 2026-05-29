"""Rebuild dbt analytics marts on a configurable schedule."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.operators.python import PythonOperator

from airflow import DAG

sys.path.insert(0, "/opt/airflow")

from shared.dbt_refresh_config import resolve_dbt_refresh_schedule

logger = logging.getLogger(__name__)

DBT_PROJECT_DIR = Path(os.getenv("DBT_PROJECT_DIR", "/opt/airflow/dbt_fraud"))
DBT_PROFILES_DIR = Path(
    os.getenv("DBT_PROFILES_DIR", str(DBT_PROJECT_DIR / "profiles" / "airflow"))
)
DBT_RUN_TIMEOUT_SECONDS = int(os.getenv("DBT_RUN_TIMEOUT_SECONDS", "600"))


def run_dbt_marts(**_context) -> dict[str, str]:
    if not DBT_PROJECT_DIR.is_dir():
        raise FileNotFoundError(f"dbt project not found: {DBT_PROJECT_DIR}")
    if not DBT_PROFILES_DIR.is_dir():
        raise FileNotFoundError(f"dbt profiles dir not found: {DBT_PROFILES_DIR}")

    cmd = [
        "dbt",
        "run",
        "--project-dir",
        str(DBT_PROJECT_DIR),
        "--profiles-dir",
        str(DBT_PROFILES_DIR),
    ]
    logger.info("Running: %s", " ".join(cmd))

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=DBT_RUN_TIMEOUT_SECONDS,
        check=False,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        logger.error("dbt run failed:\n%s", output[-8000:])
        raise RuntimeError(f"dbt run failed with exit code {proc.returncode}")

    logger.info("dbt run succeeded:\n%s", output[-4000:])
    return {"status": "ok", "project_dir": str(DBT_PROJECT_DIR)}


default_args = {
    "owner": "fraud-detection",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="dbt_marts_refresh",
    default_args=default_args,
    description="Rebuild dbt analytics marts in Postgres for the analytics dashboard",
    schedule_interval=resolve_dbt_refresh_schedule(),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["dbt", "analytics", "fraud"],
) as dag:
    PythonOperator(
        task_id="run_dbt_marts",
        python_callable=run_dbt_marts,
    )
