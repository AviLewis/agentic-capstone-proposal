"""Tests for the Settings loader (fail-fast behavior)."""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings

REQUIRED = {
    "OPENAI_API_KEY": "sk-test",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-key",
    "SUPABASE_DB_URL": "postgresql://user:pass@localhost:5432/db",
}


@pytest.fixture(autouse=True)
def _clear_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _clear_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure nothing leaks in from a real environment / .env file.
    for key in (*REQUIRED, "NOTION_TOKEN", "CONTACT_EMAIL", "SEMANTIC_SCHOLAR_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_settings_loads_with_required_env(monkeypatch: pytest.MonkeyPatch):
    _clear_required_env(monkeypatch)
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.OPENAI_API_KEY == "sk-test"
    assert settings.NOTION_TOKEN is None
    assert settings.cors_origins_list == ["http://localhost:3000"]


def test_get_settings_fails_fast_when_missing(monkeypatch: pytest.MonkeyPatch):
    _clear_required_env(monkeypatch)
    # Point env_file at a nonexistent path so .env cannot satisfy requirements.
    monkeypatch.setattr(
        Settings, "model_config", {**Settings.model_config, "env_file": None}
    )

    with pytest.raises(RuntimeError) as exc:
        get_settings()

    message = str(exc.value)
    assert "OPENAI_API_KEY" in message
    assert "SUPABASE_URL" in message
