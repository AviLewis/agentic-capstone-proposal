"""Structural checks on the SQL migration (no DB connection required)."""

from __future__ import annotations

from pathlib import Path

import pytest

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "0001_init.sql"
)

TABLES = [
    "projects",
    "runs",
    "questions",
    "papers",
    "methodologies",
    "plans",
    "scores",
]


@pytest.fixture(scope="module")
def sql() -> str:
    return MIGRATION.read_text().lower()


def test_migration_exists():
    assert MIGRATION.exists(), f"missing migration at {MIGRATION}"


@pytest.mark.parametrize("table", TABLES)
def test_creates_table(sql: str, table: str):
    assert f"create table if not exists {table}" in sql


@pytest.mark.parametrize("table", TABLES)
def test_enables_rls(sql: str, table: str):
    assert f"alter table {table}" in sql and "enable row level security" in sql


def test_foreign_keys_present(sql: str):
    assert "references projects (id) on delete cascade" in sql
    assert "references runs (id) on delete cascade" in sql
    assert "references questions (id) on delete cascade" in sql
    assert "references plans (id) on delete cascade" in sql


def test_runs_has_caps_and_cost(sql: str):
    assert "caps" in sql and "cost_used" in sql


def test_status_check_constraint(sql: str):
    for status in ("pending", "awaiting_question_selection", "capped", "error"):
        assert status in sql
