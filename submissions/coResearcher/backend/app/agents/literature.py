"""Literature Review agent: a plan -> act -> observe tool loop per question.

The agent (1) plans search queries, (2) acts by calling the multi-source search
tool, (3) observes coverage and decides whether to refine, and finally selects
the most relevant papers with a per-paper relevance rationale. Retrieved
abstracts are wrapped as untrusted data to resist prompt injection.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from pydantic import BaseModel, Field

from app.agents import StructuredInvoker
from app.graph.guards import UNTRUSTED_SYSTEM_GUIDANCE, wrap_untrusted
from app.graph.state import PaperItem
from app.llm import Usage, ainvoke_structured
from app.logging import get_logger
from app.tools.schemas import NormalizedPaper
from app.tools.search import search_all

log = get_logger(__name__)

SearchFn = Callable[..., Awaitable[list[NormalizedPaper]]]

_PLAN_SYSTEM = (
    "You are a literature search strategist. Given a research question, produce "
    "a small set of complementary search queries (keyword phrases) that together "
    "cover the key facets of the question. Prefer precise, high-signal queries."
)

_ASSESS_SYSTEM = (
    "You assess whether a set of retrieved papers sufficiently covers a research "
    "question. If coverage has clear gaps, propose refined queries to fill them; "
    "otherwise mark coverage sufficient.\n\n" + UNTRUSTED_SYSTEM_GUIDANCE
)

_SELECT_SYSTEM = (
    "You select the papers most relevant to a research question and write a one- "
    "sentence relevance rationale for each. Only keep genuinely relevant papers.\n\n"
    + UNTRUSTED_SYSTEM_GUIDANCE
)


class SearchPlan(BaseModel):
    queries: list[str] = Field(description="2-4 complementary search queries.")


class CoverageAssessment(BaseModel):
    sufficient: bool
    reasoning: str = ""
    refined_queries: list[str] = Field(default_factory=list)


class PaperRelevance(BaseModel):
    index: int = Field(description="Index of the paper in the provided list.")
    keep: bool
    relevance: str = Field(default="", description="One-sentence relevance rationale.")


class RelevanceSelection(BaseModel):
    selections: list[PaperRelevance]


def _format_papers(papers: list[NormalizedPaper]) -> str:
    lines = []
    for i, p in enumerate(papers):
        abstract = wrap_untrusted(p.abstract or "", source=p.source)
        year = p.year or "n.d."
        lines.append(f"[{i}] {p.title} ({year})\n{abstract}")
    return "\n\n".join(lines) if lines else "(no papers)"


async def plan_searches(
    question: str, *, invoke: StructuredInvoker = ainvoke_structured
) -> tuple[SearchPlan, Usage]:
    return await invoke(
        SearchPlan,
        _PLAN_SYSTEM,
        f"Research question:\n{question}\n\nPropose complementary search queries.",
        temperature=0.5,
    )


async def assess_coverage(
    question: str,
    papers: list[NormalizedPaper],
    *,
    invoke: StructuredInvoker = ainvoke_structured,
) -> tuple[CoverageAssessment, Usage]:
    human = (
        f"Research question:\n{question}\n\n"
        f"Retrieved papers so far:\n{_format_papers(papers)}\n\n"
        "Is coverage sufficient? If not, propose refined queries."
    )
    return await invoke(CoverageAssessment, _ASSESS_SYSTEM, human, temperature=0.3)


async def select_relevant(
    question: str,
    papers: list[NormalizedPaper],
    max_papers: int,
    *,
    invoke: StructuredInvoker = ainvoke_structured,
) -> tuple[RelevanceSelection, Usage]:
    human = (
        f"Research question:\n{question}\n\n"
        f"Candidate papers:\n{_format_papers(papers)}\n\n"
        f"Select up to {max_papers} most relevant papers. Return their indices, "
        "keep=true for those to include, and a one-sentence relevance rationale."
    )
    return await invoke(RelevanceSelection, _SELECT_SYSTEM, human, temperature=0.2)


class ReviewOutcome(BaseModel):
    papers: list[PaperItem]
    usage: Usage
    tool_calls: int
    queries_used: list[str]
    # Sources that failed during this review: source name -> short reason.
    source_health: dict[str, str] = Field(default_factory=dict)


async def review_question(
    question: str,
    *,
    max_papers: int = 8,
    max_tool_calls: int = 6,
    max_iterations: int = 2,
    limit_per_source: int = 6,
    sources: Sequence[str] | None = None,
    invoke: StructuredInvoker = ainvoke_structured,
    search: SearchFn = search_all,
) -> ReviewOutcome:
    """Run the plan->act->observe loop for one question."""
    usage = Usage()
    tool_calls = 0
    queries_used: list[str] = []
    collected: dict[str, NormalizedPaper] = {}
    # Accumulate per-source failures across every search call in this review.
    source_failures: dict[str, str] = {}
    search_kwargs: dict[str, Any] = {"failures": source_failures}
    if sources is not None:
        search_kwargs["sources"] = tuple(sources)

    plan, u = await plan_searches(question, invoke=invoke)
    usage += u
    queries = plan.queries[:3] or [question]

    for _iteration in range(max_iterations):
        for q in queries:
            if tool_calls >= max_tool_calls:
                break
            queries_used.append(q)
            found = await search(q, limit_per_source, **search_kwargs)
            tool_calls += 1
            for p in found:
                key = (p.doi or p.title or "").lower()
                if key:
                    collected.setdefault(key, p)

        if tool_calls >= max_tool_calls or len(collected) >= max_papers * 2:
            break

        assessment, u = await assess_coverage(
            question, list(collected.values()), invoke=invoke
        )
        usage += u
        if assessment.sufficient or not assessment.refined_queries:
            break
        queries = assessment.refined_queries[:3]

    pool = list(collected.values())
    if not pool:
        return ReviewOutcome(
            papers=[],
            usage=usage,
            tool_calls=tool_calls,
            queries_used=queries_used,
            source_health=source_failures,
        )

    selection, u = await select_relevant(question, pool, max_papers, invoke=invoke)
    usage += u

    papers: list[PaperItem] = []
    for sel in selection.selections:
        if not sel.keep or not (0 <= sel.index < len(pool)):
            continue
        p = pool[sel.index]
        papers.append(
            PaperItem(
                source=p.source,
                title=p.title,
                authors=p.authors,
                year=p.year,
                venue=p.venue,
                doi=p.doi,
                url=p.url,
                abstract=p.abstract,
                relevance=sel.relevance,
            )
        )
        if len(papers) >= max_papers:
            break

    return ReviewOutcome(
        papers=papers,
        usage=usage,
        tool_calls=tool_calls,
        queries_used=queries_used,
        source_health=source_failures,
    )
