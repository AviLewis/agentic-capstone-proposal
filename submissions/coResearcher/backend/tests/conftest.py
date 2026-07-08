"""Shared test fixtures: a stubbed LLM invoker and paper search.

These let the graph and nodes run end-to-end without hitting OpenAI or the
network. The stub returns schema-appropriate canned outputs for every structured
schema used by the agents.
"""

from __future__ import annotations

import pytest

from app.agents.ideator import GeneratedQuestion, IdeationResult
from app.agents.judge import CriterionEval, JudgeResult
from app.agents.literature import (
    CoverageAssessment,
    PaperRelevance,
    RelevanceSelection,
    SearchPlan,
)
from app.agents.methodology import MethodologyResult
from app.agents.plan import PlanResult
from app.graph.state import FEASIBILITY_RUBRIC
from app.llm import Usage
from app.tools.schemas import NormalizedPaper

_USAGE = Usage(input_tokens=10, output_tokens=5, total_tokens=15, cost_usd=0.001)


def _canned(schema):
    if schema is IdeationResult:
        return IdeationResult(
            questions=[
                GeneratedQuestion(
                    text=f"Stub research question {i + 1}?",
                    rationale="Fits the researcher's needs.",
                    tag="exploratory",
                )
                for i in range(6)
            ]
        )
    if schema is SearchPlan:
        return SearchPlan(queries=["query one", "query two"])
    if schema is CoverageAssessment:
        return CoverageAssessment(sufficient=True, reasoning="ok", refined_queries=[])
    if schema is RelevanceSelection:
        return RelevanceSelection(
            selections=[
                PaperRelevance(index=0, keep=True, relevance="Directly relevant."),
                PaperRelevance(index=1, keep=True, relevance="Provides background."),
            ]
        )
    if schema is MethodologyResult:
        return MethodologyResult(
            methods=["mixed methods"], datasets=["public dataset"], gaps=["needs labels"]
        )
    if schema is PlanResult:
        return PlanResult(
            objective="Investigate the question.",
            hypotheses=["H1"],
            methods=[{"description": "method", "source": None}],
            data=[{"description": "public dataset", "source": None}],
            risks=["data risk"],
            resources=["compute"],
        )
    if schema is JudgeResult:
        return JudgeResult(
            evaluations=[
                CriterionEval(criterion=name, score=4.0, justification="solid")
                for name in FEASIBILITY_RUBRIC
            ]
        )
    raise AssertionError(f"No canned output for schema {schema!r}")


async def fake_invoke(schema, system, human, *, temperature=0.7, model=None):
    return _canned(schema), _USAGE


async def fake_search(query, limit_per_source=6, **kwargs):
    return [
        NormalizedPaper(
            source="stub",
            title=f"Stub paper for {query}",
            authors=["A. Author"],
            year=2024,
            doi=f"10.1234/{abs(hash(query)) % 10000}",
            abstract="Stub abstract.",
        ),
        NormalizedPaper(
            source="stub",
            title=f"Second stub paper for {query}",
            authors=["B. Author"],
            year=2023,
            abstract="Another stub abstract.",
        ),
    ]


@pytest.fixture
def stub_deps(monkeypatch):
    """Monkeypatch graph node dependencies with the stubs above."""
    from app.graph import deps

    monkeypatch.setattr(deps, "invoke", fake_invoke)
    monkeypatch.setattr(deps, "search", fake_search)
    return deps
