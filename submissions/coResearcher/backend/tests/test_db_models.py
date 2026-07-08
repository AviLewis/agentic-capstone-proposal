"""Unit tests for DB models + pool guard (no live database)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest


def _now() -> datetime:
    return datetime.now(UTC)


def test_run_model_coerces_jsonb_and_defaults():
    from app.db.models import Run

    run = Run.model_validate(
        {
            "id": uuid4(),
            "project_id": uuid4(),
            "thread_id": "thread-123",
            "status": "ideating",
            "caps": {"max_questions": 6},
            "cost_used": {},
            "error": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    assert run.status == "ideating"
    assert run.caps["max_questions"] == 6


def test_paper_model_parses_authors_list():
    from app.db.models import Paper

    paper = Paper.model_validate(
        {
            "id": uuid4(),
            "question_id": uuid4(),
            "source": "openalex",
            "title": "A study",
            "authors": ["Ada Lovelace", "Alan Turing"],
            "year": 2024,
            "created_at": _now(),
        }
    )
    assert paper.authors == ["Ada Lovelace", "Alan Turing"]
    assert paper.doi is None


def test_score_model_coerces_decimal_to_float():
    from app.db.models import Score

    score = Score.model_validate(
        {
            "id": uuid4(),
            "plan_id": uuid4(),
            "criterion": "data availability",
            "score": Decimal("4.5"),
            "weight": Decimal("0.25"),
            "justification": "public datasets exist",
            "total": Decimal("3.9"),
            "created_at": _now(),
        }
    )
    assert score.score == pytest.approx(4.5)
    assert score.weight == pytest.approx(0.25)


def test_invalid_run_status_rejected():
    from pydantic import ValidationError

    from app.db.models import Run

    with pytest.raises(ValidationError):
        Run.model_validate(
            {
                "id": uuid4(),
                "project_id": uuid4(),
                "thread_id": "t",
                "status": "not-a-real-status",
                "created_at": _now(),
                "updated_at": _now(),
            }
        )


def test_get_pool_raises_before_open():
    from app.db import pool

    pool._pool = None  # ensure not initialized
    with pytest.raises(RuntimeError):
        pool.get_pool()
