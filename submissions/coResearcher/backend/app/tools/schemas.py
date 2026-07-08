"""Common schema for papers returned by literature search tools."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NormalizedPaper(BaseModel):
    """A paper normalized to a common shape across all sources."""

    source: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
