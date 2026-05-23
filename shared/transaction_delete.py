"""Cascade delete a transaction and all related fraud-scoring rows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine

_CHILD_TABLES = (
    "risk_scores_history",
    "fraud_flags",
    "risk_scores",
)


def delete_transaction_cascade(
    engine: Engine,
    transaction_id: UUID,
) -> dict[str, int] | None:
    """Delete one transaction and dependent rows. Returns per-table counts, or None if missing."""
    tid = str(transaction_id)
    counts: dict[str, int] = {}

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM transactions WHERE transaction_id = :tid"),
            {"tid": tid},
        ).scalar()
        if not exists:
            return None

        for table in _CHILD_TABLES:
            result = conn.execute(
                text(f"DELETE FROM {table} WHERE transaction_id = :tid"),
                {"tid": tid},
            )
            counts[table] = result.rowcount

        result = conn.execute(
            text("DELETE FROM transactions WHERE transaction_id = :tid"),
            {"tid": tid},
        )
        counts["transactions"] = result.rowcount

    return counts
