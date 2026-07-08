"""Ideator agent: generate diverse research questions from a brief."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents import StructuredInvoker
from app.graph.state import QuestionItem
from app.llm import Usage, ainvoke_structured

SYSTEM = (
    "You are an expert research ideation partner for PhD-level researchers. "
    "Given a research brief and the researcher's context and available data, you "
    "propose diverse, non-overlapping research questions. Each question must be "
    "specific, feasible to investigate, and clearly tied to the researcher's "
    "stated needs and constraints. Vary the questions across scope (narrow vs. "
    "broad) and novelty (incremental vs. exploratory)."
)


class GeneratedQuestion(BaseModel):
    text: str = Field(description="The research question, phrased as a question.")
    rationale: str = Field(
        description="Why this question fits the researcher's stated needs and data."
    )
    tag: str = Field(
        description="Short novelty/scope tag, e.g. 'incremental', 'exploratory', "
        "'high-risk', 'applied'."
    )


class IdeationResult(BaseModel):
    questions: list[GeneratedQuestion]


def _build_human(brief: str, researcher_context: str, own_data: str, n: int) -> str:
    parts = [
        f"Research brief:\n{brief}",
        f"Researcher context:\n{researcher_context or '(none provided)'}",
        f"Researcher's own data/constraints:\n{own_data or '(none provided)'}",
        f"\nGenerate exactly {n} diverse research questions.",
    ]
    return "\n\n".join(parts)


async def generate_questions(
    brief: str,
    researcher_context: str = "",
    own_data: str = "",
    n: int = 6,
    *,
    invoke: StructuredInvoker = ainvoke_structured,
) -> tuple[list[QuestionItem], Usage]:
    result, usage = await invoke(
        IdeationResult,
        SYSTEM,
        _build_human(brief, researcher_context, own_data, n),
        temperature=0.9,
    )
    items = [
        QuestionItem(text=q.text, rationale=q.rationale, tag=q.tag)
        for q in result.questions[:n]
    ]
    return items, usage
