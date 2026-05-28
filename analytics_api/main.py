"""FastAPI analytics API — serves dbt marts to the React dashboard."""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from shared import analytics_marts as marts

load_dotenv()

Granularity = Literal["Daily", "Monthly", "Yearly"]

app = FastAPI(
    title="Fraud Analytics API",
    version="1.0.0",
    description="Read-only JSON endpoints over dbt analytics marts in Postgres.",
)

_cors_origins = os.getenv(
    "ANALYTICS_CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _require_mart(table: str) -> None:
    if not marts.mart_exists(table):
        raise HTTPException(
            status_code=404,
            detail=f"Analytics mart `{table}` not found. Run dbt in `dbt_fraud/` first.",
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta/status")
def meta_status() -> dict:
    general_ready = marts.mart_exists("mart_general_kpis")
    velocity_ready = marts.mart_exists("mart_velocity_kpis")
    return {
        "general_ready": general_ready,
        "velocity_ready": velocity_ready,
        "fingerprint": marts.get_marts_fingerprint(),
        "auto_refresh_seconds": marts.AUTO_REFRESH_SECONDS,
    }


@app.get("/api/general/kpis")
def general_kpis() -> dict:
    _require_mart("mart_general_kpis")
    row = marts.df_first_row(marts.load_mart("mart_general_kpis"))
    return row or {}


@app.get("/api/general/currency")
def general_currency() -> list[dict]:
    _require_mart("mart_currency_breakdown")
    return marts.df_to_records(marts.load_mart("mart_currency_breakdown"))


@app.get("/api/general/top-users")
def general_top_users() -> list[dict]:
    _require_mart("mart_top_users_fraud")
    return marts.df_to_records(marts.load_mart("mart_top_users_fraud"))


@app.get("/api/general/merchants/by-count")
def general_merchants_by_count() -> list[dict]:
    _require_mart("mart_merchant_fraud_by_count")
    return marts.df_to_records(marts.load_mart("mart_merchant_fraud_by_count"))


@app.get("/api/general/merchants/by-rate")
def general_merchants_by_rate() -> list[dict]:
    _require_mart("mart_merchant_fraud_by_rate")
    return marts.df_to_records(marts.load_mart("mart_merchant_fraud_by_rate"))


@app.get("/api/general/countries/by-count")
def general_countries_by_count() -> list[dict]:
    _require_mart("mart_country_fraud_count")
    return marts.df_to_records(marts.load_mart("mart_country_fraud_count"))


@app.get("/api/general/countries/by-rate")
def general_countries_by_rate() -> list[dict]:
    _require_mart("mart_country_fraud_rate")
    return marts.df_to_records(marts.load_mart("mart_country_fraud_rate"))


@app.get("/api/general/flag-reasons")
def general_flag_reasons() -> list[dict]:
    _require_mart("mart_flag_reasons")
    return marts.df_to_records(marts.load_mart("mart_flag_reasons"))


@app.get("/api/general/trends")
def general_trends(granularity: Granularity = Query(default="Daily")) -> list[dict]:
    table = marts.GENERAL_TREND_MARTS[granularity]
    _require_mart(table)
    return marts.df_to_records(marts.load_trend(marts.GENERAL_TREND_MARTS, granularity))


@app.get("/api/velocity/kpis")
def velocity_kpis() -> dict:
    _require_mart("mart_velocity_kpis")
    row = marts.df_first_row(marts.load_mart("mart_velocity_kpis"))
    return row or {}


@app.get("/api/velocity/buckets")
def velocity_buckets() -> list[dict]:
    _require_mart("mart_velocity_buckets")
    return marts.df_to_records(marts.load_mart("mart_velocity_buckets"))


@app.get("/api/velocity/top-users")
def velocity_top_users() -> list[dict]:
    _require_mart("mart_top_users_velocity")
    return marts.df_to_records(marts.load_mart("mart_top_users_velocity"))


@app.get("/api/velocity/countries/by-count")
def velocity_countries_by_count() -> list[dict]:
    _require_mart("mart_country_velocity_count")
    return marts.df_to_records(marts.load_mart("mart_country_velocity_count"))


@app.get("/api/velocity/countries/by-rate")
def velocity_countries_by_rate() -> list[dict]:
    _require_mart("mart_country_velocity_rate")
    return marts.df_to_records(marts.load_mart("mart_country_velocity_rate"))


@app.get("/api/velocity/scatter")
def velocity_scatter() -> list[dict]:
    _require_mart("mart_velocity_scatter")
    return marts.df_to_records(marts.load_mart("mart_velocity_scatter"))


@app.get("/api/velocity/share-trend")
def velocity_share_trend(granularity: Granularity = Query(default="Daily")) -> list[dict]:
    table = marts.VELOCITY_SHARE_TREND_MARTS[granularity]
    _require_mart(table)
    return marts.df_to_records(marts.load_trend(marts.VELOCITY_SHARE_TREND_MARTS, granularity))


@app.get("/api/velocity/heatmap")
def velocity_heatmap() -> list[dict]:
    _require_mart("mart_velocity_heatmap")
    return marts.df_to_records(marts.load_mart("mart_velocity_heatmap"))


@app.get("/api/velocity/repeat-interval")
def velocity_repeat_interval() -> list[dict]:
    _require_mart("mart_repeat_interval")
    return marts.df_to_records(marts.load_mart("mart_repeat_interval"))


@app.get("/api/velocity/trends")
def velocity_trends(granularity: Granularity = Query(default="Daily")) -> list[dict]:
    table = marts.VELOCITY_TREND_MARTS[granularity]
    _require_mart(table)
    return marts.df_to_records(marts.load_trend(marts.VELOCITY_TREND_MARTS, granularity))
