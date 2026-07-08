"""API-level tests: request validation and error envelopes (no DB needed)."""

from __future__ import annotations

from uuid import uuid4

import pytest

REQUIRED_ENV = {
    "OPENAI_API_KEY": "sk-test",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-key",
    "SUPABASE_DB_URL": "postgresql://user:pass@localhost:5432/db",
}


@pytest.fixture
def client(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    from fastapi.testclient import TestClient

    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    # Not used as a context manager: lifespan (DB/graph init) does not run.
    return TestClient(create_app())


def test_create_run_validation_error_envelope(client):
    resp = client.post("/runs", json={"brief": "too short"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == 422
    assert body["error"]["message"] == "Request validation failed"
    assert isinstance(body["error"]["details"], list)


def test_get_run_invalid_uuid_envelope(client):
    resp = client.get("/runs/not-a-uuid")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == 400


def test_stream_returns_503_without_manager(client):
    resp = client.get(f"/runs/{uuid4()}/stream")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == 503


def test_resume_returns_503_without_manager(client):
    resp = client.post(f"/runs/{uuid4()}/resume", json={"resume": {}})
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == 503
