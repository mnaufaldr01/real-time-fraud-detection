"""Load analytics marts built by dbt."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fraud:fraud@localhost:5433/fraud_db")

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


@st.cache_resource
def get_engine():
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


def attach_user_sparklines(users_df: pd.DataFrame) -> pd.DataFrame:
    if users_df.empty:
        return users_df

    daily = load_mart("mart_user_fraud_daily")
    if daily.empty:
        users_df["sparkline"] = [[] for _ in range(len(users_df))]
        return users_df

    daily["report_date"] = pd.to_datetime(daily["report_date"])
    date_index = pd.date_range(
        end=daily["report_date"].max().normalize(),
        periods=14,
        freq="D",
    )

    sparklines: list[list[int]] = []
    for user_id in users_df["user_id"]:
        user_daily = daily[daily["user_id"] == user_id].set_index("report_date")
        series = (
            user_daily.reindex(date_index, fill_value=0)["fraud_count"]
            .astype(int)
            .tolist()
        )
        sparklines.append(series)

    result = users_df.copy()
    result["sparkline"] = sparklines
    return result
