"""Smoke tests for the analytics REST API."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from analytics_api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_status_without_marts():
    with patch("analytics_api.main.marts.mart_exists", return_value=False):
        response = client.get("/api/meta/status")
    assert response.status_code == 200
    body = response.json()
    assert body["general_ready"] is False
    assert body["velocity_ready"] is False
    assert body["fingerprint"] is None


def test_general_kpis_404_when_mart_missing():
    with patch("analytics_api.main.marts.mart_exists", return_value=False):
        response = client.get("/api/general/kpis")
    assert response.status_code == 404
