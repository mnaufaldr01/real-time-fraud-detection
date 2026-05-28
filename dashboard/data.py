"""Load analytics marts built by dbt."""

from __future__ import annotations

import streamlit as st

from shared import analytics_marts as marts

AUTO_REFRESH_SECONDS = marts.AUTO_REFRESH_SECONDS
GENERAL_TREND_MARTS = marts.GENERAL_TREND_MARTS
VELOCITY_TREND_MARTS = marts.VELOCITY_TREND_MARTS
VELOCITY_SHARE_TREND_MARTS = marts.VELOCITY_SHARE_TREND_MARTS


@st.cache_resource
def get_engine():
    return marts.get_engine()


def load_mart(table: str):
    return marts.load_mart(table)


def load_trend(mart_map: dict[str, str], granularity: str):
    return marts.load_trend(mart_map, granularity)


def mart_exists(table: str) -> bool:
    return marts.mart_exists(table)


def get_marts_fingerprint() -> str | None:
    return marts.get_marts_fingerprint()
