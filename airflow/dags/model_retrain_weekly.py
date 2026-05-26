"""Weekly safe-deployment retrain: static PaySim + synthetic anomaly, gated promote."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator

from airflow import DAG

sys.path.insert(0, "/opt/airflow")

from shared.model_retrain import (
    check_training_data,
    evaluate_candidates,
    promote_models,
    record_retrain_manifest,
    run_anomaly_training,
    run_classifier_training,
)

logger = logging.getLogger(__name__)


def task_check_training_data(**_context) -> dict:
    result = check_training_data()
    logger.info("Training data OK: csv=%s cache=%s", result["csv_present"], result["cache_present"])
    return result


def task_train_classifier(**_context) -> dict:
    return run_classifier_training()


def task_train_anomaly(**_context) -> dict:
    return run_anomaly_training()


def task_evaluate_holdout(**_context) -> dict:
    return evaluate_candidates()


def task_promote_or_skip(**context) -> dict:
    ti = context["ti"]
    evaluation = ti.xcom_pull(task_ids="evaluate_holdout")
    if not evaluation:
        raise RuntimeError("Missing XCom from evaluate_holdout")
    return promote_models(evaluation)


def task_record_manifest(**context) -> dict:
    ti = context["ti"]
    dag_run_id = context.get("dag_run").run_id if context.get("dag_run") else None
    return record_retrain_manifest(
        data_check=ti.xcom_pull(task_ids="check_training_data") or {},
        classifier_train=ti.xcom_pull(task_ids="train_classifier") or {},
        anomaly_train=ti.xcom_pull(task_ids="train_anomaly") or {},
        evaluation=ti.xcom_pull(task_ids="evaluate_holdout") or {},
        promotion=ti.xcom_pull(task_ids="promote_or_skip") or {},
        dag_run_id=dag_run_id,
    )


default_args = {
    "owner": "fraud-detection",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=15),
}

with DAG(
    dag_id="model_retrain_weekly",
    default_args=default_args,
    description=(
        "Safe deployment: retrain on static PaySim/synthetic data, "
        "evaluate vs production bundles, promote only if improved, write manifest"
    ),
    schedule_interval=os.getenv("MODEL_RETRAIN_SCHEDULE", "0 4 * * 0"),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["fraud", "ml", "training"],
    max_active_runs=1,
) as dag:
    check_data = PythonOperator(
        task_id="check_training_data",
        python_callable=task_check_training_data,
    )
    train_classifier = PythonOperator(
        task_id="train_classifier",
        python_callable=task_train_classifier,
        execution_timeout=timedelta(hours=2),
    )
    train_anomaly = PythonOperator(
        task_id="train_anomaly",
        python_callable=task_train_anomaly,
    )
    evaluate_holdout = PythonOperator(
        task_id="evaluate_holdout",
        python_callable=task_evaluate_holdout,
    )
    promote_or_skip = PythonOperator(
        task_id="promote_or_skip",
        python_callable=task_promote_or_skip,
    )
    record_manifest = PythonOperator(
        task_id="record_manifest",
        python_callable=task_record_manifest,
    )

    check_data >> train_classifier >> train_anomaly >> evaluate_holdout >> promote_or_skip >> record_manifest
