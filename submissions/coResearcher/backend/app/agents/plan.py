"""Research Plan agent: produce a structured plan for a question."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.agents import StructuredInvoker
from app.graph.state import MethodologyItem, PaperItem
from app.llm import Usage, ainvoke_structured

SYSTEM = (
    "You are a research planning expert. Given a research question, its proposed "
    "methodology, and the papers found during literature review, produce a "
    "concrete, structured research plan. Be specific and realistic about scope "
    "and resources. When a method or a data source comes from, adapts, or is "
    "described in one of the provided papers, cite that paper by its exact title."
)


class MethodStep(BaseModel):
    description: str = Field(
        description="A concrete method or step, and how it will be applied."
    )
    source: str | None = Field(
        default=None,
        description=(
            "The exact title of the paper from the provided papers list that "
            "introduces, adapts, or describes this method, or null if none apply."
        ),
    )


class DataSource(BaseModel):
    description: str = Field(
        description="A dataset or data source and how it will be used."
    )
    source: str | None = Field(
        default=None,
        description=(
            "The exact title of the paper from the provided papers list that "
            "introduces, provides, or describes this data, or null if none apply."
        ),
    )


class PlanResult(BaseModel):
    objective: str = Field(description="The primary objective of the study.")
    hypotheses: list[str] = Field(description="Testable hypotheses or research aims.")
    methods: list[MethodStep] = Field(
        description="Concrete methods/steps, each optionally citing the paper it comes from."
    )
    data: list[DataSource] = Field(
        description="Data sources, each optionally citing the paper it comes from."
    )
    risks: list[str] = Field(description="Key risks and mitigations.")
    resources: list[str] = Field(description="Required resources/skills/tools.")


def _papers_block(papers: list[PaperItem] | None) -> str:
    if not papers:
        return "(none)"
    lines: list[str] = []
    for p in papers:
        meta = ", ".join(str(a) for a in p.authors[:2])
        if p.year:
            meta = f"{meta} {p.year}".strip()
        suffix = f" ({meta})" if meta else ""
        lines.append(f"- {p.title}{suffix}")
    return "\n".join(lines)


async def draft_plan(
    question: str,
    methodology: MethodologyItem | None = None,
    papers: list[PaperItem] | None = None,
    *,
    invoke: StructuredInvoker = ainvoke_structured,
) -> tuple[dict[str, Any], Usage]:
    method_block = "(none)"
    if methodology is not None:
        method_block = (
            f"methods: {', '.join(methodology.methods) or '-'}\n"
            f"datasets: {', '.join(methodology.datasets) or '-'}\n"
            f"gaps: {', '.join(methodology.gaps) or '-'}"
        )
    human = (
        f"Research question:\n{question}\n\n"
        f"Proposed methodology:\n{method_block}\n\n"
        f"Papers from literature review:\n{_papers_block(papers)}\n\n"
        "Produce a structured research plan. For each method and each data "
        "source, set 'source' to the exact title of the paper above that it is "
        "drawn from, or null if no listed paper applies."
    )
    result, usage = await invoke(PlanResult, SYSTEM, human, temperature=0.5)
    return result.model_dump(), usage
