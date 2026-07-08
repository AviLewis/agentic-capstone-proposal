"""Export orchestration: guard behind HITL approval, then create a Notion page."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.db import repository
from app.logging import get_logger
from app.notion.render import plan_title, plan_to_blocks

log = get_logger(__name__)


class ExportNotApprovedError(RuntimeError):
    """The run has not completed the post-judge approval gate."""


class ExportPlanNotFoundError(RuntimeError):
    """The approved plan could not be found."""


class ExportPlanMismatchError(RuntimeError):
    """A specific plan was requested that is not the approved plan."""


class Exporter(Protocol):
    async def create_page(self, title: str, blocks: list[dict[str, Any]]) -> str: ...


async def _approved_plan_id(graph, thread_id: str) -> str:
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    values = state.values or {}
    approved = values.get("approved_plan_id")
    if values.get("status") != "completed" or not approved:
        raise ExportNotApprovedError(
            "Plan export requires the post-judge approval gate to be completed."
        )
    return approved


async def export_plan(
    thread_id: str,
    *,
    graph,
    exporter: Exporter,
    requested_plan_id: str | None = None,
) -> dict[str, str]:
    """Export the approved plan for a run to Notion and persist the page URL."""
    approved = await _approved_plan_id(graph, thread_id)
    if requested_plan_id and requested_plan_id != approved:
        raise ExportPlanMismatchError(
            "Requested plan is not the approved plan for this run."
        )

    plan = await repository.get_plan(UUID(approved))
    if plan is None:
        raise ExportPlanNotFoundError(approved)

    scores = await repository.get_scores_for_plan(plan.id)
    question = await repository.get_question(plan.question_id)
    question_text = question.text if question else ""
    papers = await repository.get_papers_for_question(plan.question_id)

    title = plan_title(plan.content_json, question_text)
    blocks = plan_to_blocks(
        plan.content_json,
        [s.model_dump() for s in scores],
        question_text,
        papers=[p.model_dump() for p in papers],
    )

    url = await exporter.create_page(title, blocks)
    await repository.set_plan_notion_url(plan.id, url)
    log.info("plan_exported", plan_id=str(plan.id), url=url)
    return {"plan_id": str(plan.id), "notion_url": url}
