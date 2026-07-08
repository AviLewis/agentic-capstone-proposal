"""Request/response schemas for the runs API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.enums import RunStatus
from app.graph.state import DEFAULT_CAPS, Caps
from app.tools.search import ALLOWED_SOURCES


class CapsOverride(BaseModel):
    """Optional per-run overrides for the default caps/budget."""

    max_questions: int | None = Field(default=None, ge=1, le=20)
    max_papers_per_question: int | None = Field(default=None, ge=1, le=50)
    max_tool_calls: int | None = Field(default=None, ge=1, le=500)
    token_ceiling: int | None = Field(default=None, ge=1000)
    cost_ceiling_usd: float | None = Field(default=None, gt=0)
    wall_clock_seconds: int | None = Field(default=None, ge=30, le=7200)

    def merged(self) -> Caps:
        base = DEFAULT_CAPS.model_dump()
        overrides = {k: v for k, v in self.model_dump().items() if v is not None}
        return Caps(**{**base, **overrides})


class CreateRunRequest(BaseModel):
    brief: str = Field(min_length=10, max_length=8000)
    researcher_context: str = Field(default="", max_length=8000)
    own_data: str = Field(default="", max_length=8000)
    caps: CapsOverride | None = None
    # Literature sources to query. None = backend defaults. Must be a non-empty
    # subset of the known sources; unknown names are rejected.
    sources: list[str] | None = None

    @field_validator("sources")
    @classmethod
    def _validate_sources(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        allowed = set(ALLOWED_SOURCES)
        cleaned = [s for s in dict.fromkeys(v) if s in allowed]
        if not cleaned:
            raise ValueError(
                f"sources must be a non-empty subset of {sorted(allowed)}"
            )
        return cleaned


class CreateRunResponse(BaseModel):
    run_id: str
    thread_id: str
    status: RunStatus


class ResumeRequest(BaseModel):
    """HITL resume payload.

    For question selection: ``{"selected_ids": [...]}`` or
    ``{"selected_indexes": [...]}`` (optionally with ``edits``).
    For plan approval: ``{"approved_plan_id": "..."}`` or
    ``{"approved_index": 0}``.
    """

    resume: dict[str, Any] = Field(default_factory=dict)


class RunAcceptedResponse(BaseModel):
    run_id: str
    status: str


class ExportRequest(BaseModel):
    plan_id: str | None = None


class ExportResponse(BaseModel):
    plan_id: str
    notion_url: str


class ErrorBody(BaseModel):
    code: int
    message: str
    details: Any | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
