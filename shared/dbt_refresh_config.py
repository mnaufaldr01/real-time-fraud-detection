"""Configurable schedule for rebuilding dbt analytics marts."""

from __future__ import annotations

import os
from typing import Mapping


def resolve_dbt_refresh_schedule(environ: Mapping[str, str] | None = None) -> str | None:
    """Return cron schedule for dbt refresh, or None when disabled (manual only)."""
    env = environ if environ is not None else os.environ

    enabled = env.get("DBT_REFRESH_ENABLED", "true").lower() in ("1", "true", "yes")
    if not enabled:
        return None

    explicit = env.get("DBT_REFRESH_SCHEDULE", "").strip()
    if explicit:
        return explicit

    minutes = int(env.get("DBT_REFRESH_INTERVAL_MINUTES", "10"))
    if minutes < 1 or minutes > 59:
        raise ValueError("DBT_REFRESH_INTERVAL_MINUTES must be between 1 and 59")
    return f"*/{minutes} * * * *"
