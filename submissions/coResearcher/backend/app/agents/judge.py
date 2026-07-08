"""Judge agent: score a plan against the weighted feasibility rubric."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.agents import StructuredInvoker
from app.graph.state import FEASIBILITY_RUBRIC, CriterionScore
from app.llm import Usage, ainvoke_structured

# Human-readable descriptions for each rubric criterion.
RUBRIC_DESCRIPTIONS: dict[str, str] = {
    "data_availability": "Are the required data available or realistically obtainable?",
    "methodological_soundness": "Are the methods appropriate and rigorous?",
    "scope_time_realism": "Is the scope achievable in a realistic timeframe?",
    "novelty": "Does the plan offer novelty relative to prior work?",
    "resource_skill_fit": "Do required resources/skills match what's available?",
}

SYSTEM = (
    "You are a rigorous research feasibility judge. Score the given research plan "
    "on each rubric criterion using a 1-5 scale (1=poor, 5=excellent), with a "
    "concise justification for each score. Be critical and calibrated."
)


class CriterionEval(BaseModel):
    criterion: str = Field(description="The rubric criterion key being scored.")
    score: float = Field(description="Score from 1 (poor) to 5 (excellent).")
    justification: str


class JudgeResult(BaseModel):
    evaluations: list[CriterionEval]


def _rubric_block() -> str:
    return "\n".join(
        f"- {name} (weight {FEASIBILITY_RUBRIC[name]:.2f}): {desc}"
        for name, desc in RUBRIC_DESCRIPTIONS.items()
    )


async def evaluate_plan(
    question: str,
    plan_content: dict,
    *,
    invoke: StructuredInvoker = ainvoke_structured,
) -> tuple[list[CriterionScore], Usage]:
    """Return per-criterion scores (with rubric weights attached) + usage."""
    human = (
        f"Research question:\n{question}\n\n"
        f"Research plan (JSON):\n{json.dumps(plan_content, indent=2)}\n\n"
        f"Score the plan on each of these criteria:\n{_rubric_block()}"
    )
    result, usage = await invoke(JudgeResult, SYSTEM, human, temperature=0.2)

    by_criterion = {e.criterion: e for e in result.evaluations}
    scores: list[CriterionScore] = []
    for name, weight in FEASIBILITY_RUBRIC.items():
        ev = by_criterion.get(name)
        score_val = float(ev.score) if ev else 0.0
        scores.append(
            CriterionScore(
                criterion=name,
                score=max(0.0, min(5.0, score_val)),
                weight=weight,
                justification=ev.justification if ev else "No score returned.",
            )
        )
    return scores, usage
