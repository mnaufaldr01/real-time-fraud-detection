"""FastAPI analytics API — serves dbt marts to the React dashboard."""

from __future__ import annotations

import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from shared import analytics_filters as filters
from shared import analytics_marts as marts

load_dotenv()

Granularity = str

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


def parse_date_filter(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
) -> tuple[int | None, int | None]:
    if month is not None and year is None:
        raise HTTPException(status_code=400, detail="`month` requires `year`.")
    return year, month


DateFilter = Annotated[tuple[int | None, int | None], Depends(parse_date_filter)]


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
def general_kpis(date_filter: DateFilter) -> dict:
    _require_mart("mart_general_kpis")
    year, month = date_filter
    return filters.general_kpis(year, month) or {}


@app.get("/api/general/currency")
def general_currency(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_currency_breakdown")
    year, month = date_filter
    return filters.general_currency(year, month)


@app.get("/api/general/top-users")
def general_top_users(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_top_users_fraud")
    year, month = date_filter
    return filters.general_top_users(year, month)


@app.get("/api/general/merchants/by-count")
def general_merchants_by_count(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_merchant_fraud_by_count")
    year, month = date_filter
    return filters.general_merchants_by_count(year, month)


@app.get("/api/general/merchants/by-rate")
def general_merchants_by_rate(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_merchant_fraud_by_rate")
    year, month = date_filter
    return filters.general_merchants_by_rate(year, month)


@app.get("/api/general/countries/by-count")
def general_countries_by_count(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_country_fraud_count")
    year, month = date_filter
    return filters.general_countries_by_count(year, month)


@app.get("/api/general/countries/by-rate")
def general_countries_by_rate(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_country_fraud_rate")
    year, month = date_filter
    return filters.general_countries_by_rate(year, month)


@app.get("/api/general/flag-reasons")
def general_flag_reasons(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_flag_reasons")
    year, month = date_filter
    return filters.general_flag_reasons(year, month)


@app.get("/api/general/trends")
def general_trends(
    date_filter: DateFilter,
    granularity: str = Query(default="Daily"),
) -> list[dict]:
    table = marts.GENERAL_TREND_MARTS[granularity]
    _require_mart(table)
    year, month = date_filter
    df = filters.load_trend_filtered(marts.GENERAL_TREND_MARTS, granularity, year, month)
    return marts.df_to_records(df)


@app.get("/api/velocity/kpis")
def velocity_kpis(date_filter: DateFilter) -> dict:
    _require_mart("mart_velocity_kpis")
    year, month = date_filter
    return filters.velocity_kpis(year, month) or {}


@app.get("/api/velocity/buckets")
def velocity_buckets(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_velocity_buckets")
    year, month = date_filter
    return filters.velocity_buckets(year, month)


@app.get("/api/velocity/top-users")
def velocity_top_users(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_top_users_velocity")
    year, month = date_filter
    return filters.velocity_top_users(year, month)


@app.get("/api/velocity/countries/by-count")
def velocity_countries_by_count(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_country_velocity_count")
    year, month = date_filter
    return filters.velocity_countries_by_count(year, month)


@app.get("/api/velocity/countries/by-rate")
def velocity_countries_by_rate(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_country_velocity_rate")
    year, month = date_filter
    return filters.velocity_countries_by_rate(year, month)


@app.get("/api/velocity/scatter")
def velocity_scatter(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_velocity_scatter")
    year, month = date_filter
    return filters.velocity_scatter(year, month)


@app.get("/api/velocity/share-trend")
def velocity_share_trend(
    date_filter: DateFilter,
    granularity: str = Query(default="Daily"),
) -> list[dict]:
    table = marts.VELOCITY_SHARE_TREND_MARTS[granularity]
    _require_mart(table)
    year, month = date_filter
    df = filters.load_trend_filtered(marts.VELOCITY_SHARE_TREND_MARTS, granularity, year, month)
    return marts.df_to_records(df)


@app.get("/api/velocity/heatmap")
def velocity_heatmap(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_velocity_heatmap")
    year, month = date_filter
    return filters.velocity_heatmap(year, month)


@app.get("/api/velocity/repeat-interval")
def velocity_repeat_interval(date_filter: DateFilter) -> list[dict]:
    _require_mart("mart_repeat_interval")
    year, month = date_filter
    return filters.velocity_repeat_interval(year, month)


@app.get("/api/velocity/trends")
def velocity_trends(
    date_filter: DateFilter,
    granularity: str = Query(default="Daily"),
) -> list[dict]:
    table = marts.VELOCITY_TREND_MARTS[granularity]
    _require_mart(table)
    year, month = date_filter
    df = filters.load_trend_filtered(marts.VELOCITY_TREND_MARTS, granularity, year, month)
    return marts.df_to_records(df)
