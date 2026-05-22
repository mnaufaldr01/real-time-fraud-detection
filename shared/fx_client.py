"""Fetch FX rates from fxratesapi.com and persist snapshots to Postgres."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.engine import Engine

from shared.fx import merge_rates

logger = logging.getLogger(__name__)

FXRATESAPI_BASE = "https://api.fxratesapi.com/latest"
FX_CURRENCIES = "EUR,GBP,AUD,SGD,IDR"


def normalize_fxratesapi_response(data: dict[str, Any]) -> dict[str, float]:
    """Convert fxratesapi JSON (foreign per 1 USD) to USD per 1 unit."""
    if not data.get("success", False):
        raise ValueError(f"FX API returned success=false: {data}")

    api_rates = data.get("rates")
    if not isinstance(api_rates, dict) or not api_rates:
        raise ValueError(f"FX API missing rates: {data}")

    usd_per_unit: dict[str, float] = {"USD": 1.0}
    for code, foreign_per_usd in api_rates.items():
        if foreign_per_usd == 0:
            raise ValueError(f"FX API returned zero rate for {code}")
        usd_per_unit[code.upper()] = 1.0 / float(foreign_per_usd)

    return merge_rates(usd_per_unit)


def _parse_as_of(data: dict[str, Any]) -> datetime:
    date_str = data.get("date")
    if isinstance(date_str, str):
        try:
            parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def fetch_latest_rates(api_key: str, timeout: float = 10.0) -> tuple[dict[str, float], datetime]:
    """Fetch latest rates from fxratesapi.com."""
    if not api_key:
        raise ValueError("FX_API_KEY is not set")

    params = urlencode({"api_key": api_key, "currencies": FX_CURRENCIES})
    url = f"{FXRATESAPI_BASE}?{params}"
    request = Request(url, headers={"Accept": "application/json"})

    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"FX API request failed: {exc}") from exc

    rates = normalize_fxratesapi_response(data)
    return rates, _parse_as_of(data)


def persist_snapshot(
    engine: Engine,
    rates: dict[str, float],
    as_of: datetime,
    source: str = "fxratesapi",
) -> int:
    """Insert a rate snapshot and return its id."""
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO fx_rate_snapshots (as_of, source, rates)
                VALUES (:as_of, :source, CAST(:rates AS jsonb))
                RETURNING id
                """
            ),
            {
                "as_of": as_of,
                "source": source,
                "rates": json.dumps(rates),
            },
        ).fetchone()
    return int(row[0])
