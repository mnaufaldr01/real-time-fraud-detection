"""Tests for dbt refresh schedule configuration."""

from __future__ import annotations

import pytest

from shared.dbt_refresh_config import resolve_dbt_refresh_schedule


def test_default_interval_schedule():
    assert (
        resolve_dbt_refresh_schedule(
            {
                "DBT_REFRESH_ENABLED": "true",
                "DBT_REFRESH_INTERVAL_MINUTES": "10",
            }
        )
        == "*/10 * * * *"
    )


def test_explicit_cron_overrides_interval():
    assert (
        resolve_dbt_refresh_schedule(
            {
                "DBT_REFRESH_ENABLED": "true",
                "DBT_REFRESH_INTERVAL_MINUTES": "10",
                "DBT_REFRESH_SCHEDULE": "*/15 * * * *",
            }
        )
        == "*/15 * * * *"
    )


def test_disabled_returns_none():
    assert resolve_dbt_refresh_schedule({"DBT_REFRESH_ENABLED": "false"}) is None


def test_invalid_interval_raises():
    with pytest.raises(ValueError, match="1 and 59"):
        resolve_dbt_refresh_schedule(
            {
                "DBT_REFRESH_ENABLED": "true",
                "DBT_REFRESH_INTERVAL_MINUTES": "0",
            }
        )
