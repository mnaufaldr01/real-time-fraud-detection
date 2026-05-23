"""Unit tests for DB-backed FX snapshot provider."""

import json
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

from shared.fx import DEFAULT_FX_RATES
from shared.fx_provider import DbFxSnapshotProvider


def _mock_engine_with_row(snapshot_id: int, as_of: datetime, rates: dict):
    row = (snapshot_id, as_of, rates)
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = row
    engine = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    return engine


def _mock_engine_empty():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    engine = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    return engine


def test_loads_snapshot_from_db():
    as_of = datetime(2026, 5, 22, 4, 20, tzinfo=timezone.utc)
    rates = {"USD": 1.0, "EUR": 1.16, "GBP": 1.34}
    engine = _mock_engine_with_row(42, as_of, rates)
    provider = DbFxSnapshotProvider(engine, cache_ttl_seconds=300)

    snapshot = provider.get_snapshot()

    assert snapshot.snapshot_id == 42
    assert snapshot.as_of == as_of
    assert snapshot.rates["EUR"] == 1.16
    assert snapshot.source == "db"


def test_falls_back_to_static_when_empty():
    engine = _mock_engine_empty()
    provider = DbFxSnapshotProvider(engine)

    snapshot = provider.get_snapshot()

    assert snapshot.snapshot_id is None
    assert snapshot.source == "static"
    assert snapshot.rates == DEFAULT_FX_RATES


def test_cache_avoids_repeated_db_reads():
    as_of = datetime.now(timezone.utc)
    engine = _mock_engine_with_row(1, as_of, {"USD": 1.0, "EUR": 1.1})
    provider = DbFxSnapshotProvider(engine, cache_ttl_seconds=300)

    provider.get_snapshot()
    provider.get_snapshot()

    assert engine.connect.call_count == 1


def test_cache_expires_after_ttl():
    as_of = datetime.now(timezone.utc)
    engine = _mock_engine_with_row(1, as_of, {"USD": 1.0, "EUR": 1.1})
    provider = DbFxSnapshotProvider(engine, cache_ttl_seconds=1)
    provider._cached_at = time.monotonic() - 2

    provider.get_snapshot()

    assert engine.connect.call_count == 1


def test_parses_json_string_rates():
    as_of = datetime.now(timezone.utc)
    rates_json = json.dumps({"USD": 1.0, "GBP": 1.27})
    engine = _mock_engine_with_row(7, as_of, rates_json)
    provider = DbFxSnapshotProvider(engine)

    snapshot = provider.get_snapshot()

    assert snapshot.rates["GBP"] == 1.27
