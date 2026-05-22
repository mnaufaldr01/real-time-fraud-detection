"""Read FX rate snapshots from Postgres with in-memory caching."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from shared.fx import DEFAULT_FX_RATES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FxSnapshot:
    snapshot_id: int | None
    as_of: datetime
    rates: dict[str, float]
    source: str  # "db" | "static"


class DbFxSnapshotProvider:
    """Load latest FX snapshot from Postgres; cache in memory for TTL seconds."""

    def __init__(
        self,
        engine: Engine,
        *,
        cache_ttl_seconds: int = 300,
        stale_threshold_seconds: int = 600,
    ):
        self.engine = engine
        self.cache_ttl_seconds = cache_ttl_seconds
        self.stale_threshold_seconds = stale_threshold_seconds
        self._cached: FxSnapshot | None = None
        self._cached_at: float = 0.0

    def get_snapshot(self) -> FxSnapshot:
        now_mono = time.monotonic()
        if self._cached is not None and (now_mono - self._cached_at) < self.cache_ttl_seconds:
            return self._cached

        snapshot = self._load_from_db()
        self._cached = snapshot
        self._cached_at = now_mono
        return snapshot

    def _load_from_db(self) -> FxSnapshot:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, as_of, rates
                    FROM fx_rate_snapshots
                    ORDER BY as_of DESC
                    LIMIT 1
                    """
                )
            ).fetchone()

        if row is None:
            logger.warning("No FX snapshot in database; using static fallback rates")
            return FxSnapshot(
                snapshot_id=None,
                as_of=datetime.now(timezone.utc),
                rates=dict(DEFAULT_FX_RATES),
                source="static",
            )

        snapshot_id = int(row[0])
        as_of = row[1]
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        raw_rates = row[2]
        if isinstance(raw_rates, str):
            rates = {k.upper(): float(v) for k, v in json.loads(raw_rates).items()}
        else:
            rates = {k.upper(): float(v) for k, v in raw_rates.items()}

        age_seconds = (datetime.now(timezone.utc) - as_of).total_seconds()
        if age_seconds > self.stale_threshold_seconds:
            logger.warning(
                "FX snapshot id=%s is stale (age=%.0fs, threshold=%ss)",
                snapshot_id,
                age_seconds,
                self.stale_threshold_seconds,
            )

        return FxSnapshot(
            snapshot_id=snapshot_id,
            as_of=as_of,
            rates=rates,
            source="db",
        )
