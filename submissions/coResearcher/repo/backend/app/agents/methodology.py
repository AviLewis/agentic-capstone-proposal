"""Methodology agent: synthesize methods/datasets and flag data gaps."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents import StructuredInvoker
from app.graph.guards import UNTRUSTED_SYSTEM_GUIDANCE, wrap_untrusted
from app.graph.state import MethodologyItem, PaperItem
from app.llm import Usage, ainvoke_structured

SYSTEM = (
    "You are a research methodology advisor. Given a research question, relevant "
    "literature, and the researcher's own data/constraints, propose a coherent "
    "methodology: candidate methods (possibly combined), candidate datasets "
    "(from the literature and/or the researcher's own data), and explicit data "
    "gaps that must be resolved. Merge the researcher's own data with what the "
    "literature offers, and be concrete.\n\n" + UNTRUSTED_SYSTEM_GUIDANCE
)


class MethodologyResult(BaseModel):
    methods: list[str] = Field(description="Candidate methods or method combinations.")
    datasets: list[str] = Field(description="Candidate datasets/data sources.")
    gaps: list[str] = Field(description="Data or methodological gaps to resolve.")


def _format_papers(papers: list[PaperItem]) -> str:
    if not papers:
        return "(no papers)"
    lines = []
    for p in papers:
        abstract = wrap_untrusted(p.abstract or "", source=p.source)
        lines.append(f"- {p.title} ({p.year or 'n.d.'})\n{abstract}")
    return "\n".join(lines)


async def synthesize(
    question: str,
    papers: list[PaperItem],
    own_data: str = "",
    *,
    invoke: StructuredInvoker = ainvoke_structured,
) -> tuple[MethodologyItem, Usage]:
    human = (
        f"Research question:\n{question}\n\n"
        f"Researcher's own data/constraints:\n{own_data or '(none provided)'}\n\n"
        f"Relevant literature:\n{_format_papers(papers)}\n\n"
        "Propose methods, datasets, and flag data gaps."
    )
    result, usage = await invoke(MethodologyResult, SYSTEM, human, temperature=0.4)
    item = MethodologyItem(
        methods=result.methods, datasets=result.datasets, gaps=result.gaps
    )
    return item, usage
