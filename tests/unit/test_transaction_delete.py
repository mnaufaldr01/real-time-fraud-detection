"""Unit tests for cascade transaction delete."""

from unittest.mock import MagicMock, patch
from uuid import UUID

from shared.transaction_delete import delete_transaction_cascade

TXN_ID = UUID("11111111-1111-1111-1111-111111111111")


def _mock_engine(exists: bool, rowcounts: dict[str, int]):
    conn = MagicMock()
    conn.execute.side_effect = [
        MagicMock(scalar=lambda: 1 if exists else None),
        *[MagicMock(rowcount=rowcounts.get(t, 0)) for t in (
            "risk_scores_history",
            "fraud_flags",
            "risk_scores",
            "transactions",
        )],
    ]
    begin = MagicMock()
    begin.__enter__ = MagicMock(return_value=conn)
    begin.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.begin.return_value = begin
    return engine


def test_delete_returns_none_when_missing():
    engine = _mock_engine(exists=False, rowcounts={})
    assert delete_transaction_cascade(engine, TXN_ID) is None


def test_delete_returns_counts_when_found():
    engine = _mock_engine(
        exists=True,
        rowcounts={
            "risk_scores_history": 2,
            "fraud_flags": 1,
            "risk_scores": 1,
            "transactions": 1,
        },
    )
    result = delete_transaction_cascade(engine, TXN_ID)
    assert result == {
        "risk_scores_history": 2,
        "fraud_flags": 1,
        "risk_scores": 1,
        "transactions": 1,
    }


def test_delete_api_not_found():
    from fastapi.testclient import TestClient

    from producer.api.main import app

    with patch("producer.api.main.delete_transaction_cascade", return_value=None):
        client = TestClient(app)
        response = client.delete(f"/transactions/{TXN_ID}")

    assert response.status_code == 404


def test_delete_api_success():
    from fastapi.testclient import TestClient

    from producer.api.main import app

    counts = {"risk_scores_history": 0, "fraud_flags": 1, "risk_scores": 1, "transactions": 1}
    with patch("producer.api.main.delete_transaction_cascade", return_value=counts):
        client = TestClient(app)
        response = client.delete(f"/transactions/{TXN_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "deleted"
    assert body["transaction_id"] == str(TXN_ID)
    assert body["deleted_rows"] == counts
