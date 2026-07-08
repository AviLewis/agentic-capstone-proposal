"""Smoke test for the health endpoint."""

from __future__ import annotations

import pytest

REQUIRED = {
    "OPENAI_API_KEY": "sk-test",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-key",
    "SUPABASE_DB_URL": "postgresql://user:pass@localhost:5432/db",
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)

    from fastapi.testclient import TestClient

    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    return TestClient(create_app())


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
