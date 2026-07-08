"""Pydantic models mirroring the Supabase domain tables.

These double as the typed I/O for the DB access layer and (later) API responses.
Field names and types match the columns in ``supabase/migrations/0001_init.sql``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import PaperSource, RunStatus

__all__ = ["PaperSource", "RunStatus"]  # re-exported for convenience


class _ORMModel(BaseModel):
    """Base model that accepts DB rows (dicts) and coerces DB types."""

    model_config = ConfigDict(from_attributes=True)


class Project(_ORMModel):
    id: UUID
    brief: str
    researcher_context: str | None = None
    own_data: str | None = None
    created_at: datetime
    updated_at: datetime


class Run(_ORMModel):
    id: UUID
    project_id: UUID
    thread_id: str
    status: RunStatus
    caps: dict[str, Any] = Field(default_factory=dict)
    cost_used: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class Question(_ORMModel):
    id: UUID
    run_id: UUID
    text: str
    rationale: str | None = None
    tag: str | None = None
    selected: bool = False
    position: int = 0
    created_at: datetime


class Paper(_ORMModel):
    id: UUID
    question_id: UUID
    source: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    relevance: str | None = None
    created_at: datetime


class Methodology(_ORMModel):
    id: UUID
    question_id: UUID
    methods: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class Plan(_ORMModel):
    id: UUID
    question_id: UUID
    content_json: dict[str, Any] = Field(default_factory=dict)
    feasibility_total: float | None = None
    rank: int | None = None
    notion_url: str | None = None
    created_at: datetime
    updated_at: datetime


class Score(_ORMModel):
    id: UUID
    plan_id: UUID
    criterion: str
    score: float
    weight: float
    justification: str | None = None
    total: float | None = None
    created_at: datetime


# --- Input payloads (no server-generated fields) ----------------------------


class QuestionInput(BaseModel):
    text: str
    rationale: str | None = None
    tag: str | None = None
    selected: bool = False
    position: int = 0


class PaperInput(BaseModel):
    source: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    relevance: str | None = None


class MethodologyInput(BaseModel):
    methods: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ScoreInput(BaseModel):
    criterion: str
    score: float
    weight: float
    justification: str | None = None
    total: float | None = None


# --- Aggregate result shape --------------------------------------------------


class RankedPlan(BaseModel):
    plan: Plan
    scores: list[Score] = Field(default_factory=list)


class RunResults(BaseModel):
    run: Run
    project: Project
    questions: list[Question] = Field(default_factory=list)
    papers: list[Paper] = Field(default_factory=list)
    methodologies: list[Methodology] = Field(default_factory=list)
    ranked_plans: list[RankedPlan] = Field(default_factory=list)
