"""Unit tests for each agent with a stubbed LLM invoker (no network)."""

from __future__ import annotations

import pytest

from app.agents import ideator, judge, literature, methodology, plan
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
from app.graph.state import FEASIBILITY_RUBRIC, MethodologyItem
from app.llm import Usage
from app.tools.schemas import NormalizedPaper

USAGE = Usage(input_tokens=4, output_tokens=2, total_tokens=6, cost_usd=0.0001)


def make_invoke(mapping):
    async def invoke(schema, system, human, *, temperature=0.7, model=None):
        return mapping[schema], USAGE

    return invoke


@pytest.mark.asyncio
async def test_ideator_generates_n_questions():
    invoke = make_invoke(
        {
            IdeationResult: IdeationResult(
                questions=[
                    GeneratedQuestion(text=f"Q{i}", rationale="r", tag="t")
                    for i in range(6)
                ]
            )
        }
    )
    items, usage = await ideator.generate_questions("brief", n=3, invoke=invoke)
    assert len(items) == 3
    assert all(q.text for q in items)
    assert usage.total_tokens == 6


@pytest.mark.asyncio
async def test_literature_review_loop_selects_papers():
    async def fake_search(query, limit_per_source=6, **kwargs):
        return [
            NormalizedPaper(source="s", title="P1", doi="10.1/a", abstract="a"),
            NormalizedPaper(source="s", title="P2", abstract="b"),
        ]

    invoke = make_invoke(
        {
            SearchPlan: SearchPlan(queries=["q1"]),
            CoverageAssessment: CoverageAssessment(sufficient=True),
            RelevanceSelection: RelevanceSelection(
                selections=[
                    PaperRelevance(index=0, keep=True, relevance="relevant"),
                    PaperRelevance(index=1, keep=False, relevance="no"),
                ]
            ),
        }
    )
    outcome = await literature.review_question(
        "What is X?", max_papers=5, invoke=invoke, search=fake_search
    )
    assert len(outcome.papers) == 1
    assert outcome.papers[0].relevance == "relevant"
    assert outcome.tool_calls >= 1


@pytest.mark.asyncio
async def test_methodology_synthesize():
    invoke = make_invoke(
        {
            MethodologyResult: MethodologyResult(
                methods=["m"], datasets=["d"], gaps=["g"]
            )
        }
    )
    item, _ = await methodology.synthesize("Q?", [], own_data="my data", invoke=invoke)
    assert item.methods == ["m"]
    assert item.gaps == ["g"]


@pytest.mark.asyncio
async def test_plan_draft_returns_structured_content():
    invoke = make_invoke(
        {
            PlanResult: PlanResult(
                objective="obj",
                hypotheses=["h"],
                methods=[{"description": "m", "source": "Deep Nets"}],
                data=[{"description": "d", "source": None}],
                risks=["r"],
                resources=["res"],
            )
        }
    )
    content, _ = await plan.draft_plan(
        "Q?", MethodologyItem(methods=["m"]), invoke=invoke
    )
    assert content["objective"] == "obj"
    assert content["hypotheses"] == ["h"]
    # Methods carry an optional source citation, like data sources.
    assert content["methods"] == [{"description": "m", "source": "Deep Nets"}]


@pytest.mark.asyncio
async def test_judge_returns_weighted_criteria_and_clamps():
    invoke = make_invoke(
        {
            JudgeResult: JudgeResult(
                evaluations=[
                    CriterionEval(criterion=name, score=9.0, justification="j")
                    for name in FEASIBILITY_RUBRIC
                ]
            )
        }
    )
    scores, _ = await judge.evaluate_plan("Q?", {"objective": "o"}, invoke=invoke)
    assert len(scores) == len(FEASIBILITY_RUBRIC)
    # Scores are clamped to the 0-5 range.
    assert all(s.score == 5.0 for s in scores)
    # Weights come from the rubric.
    assert {s.weight for s in scores} == set(FEASIBILITY_RUBRIC.values())
