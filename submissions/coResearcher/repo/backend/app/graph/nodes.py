"""Graph node implementations wiring the real agents.

Each processing node: (1) enforces the budget, (2) runs its agent(s) via the
injectable ``deps``, (3) accumulates token/cost/tool-call usage, and (4)
persists results to the database when a ``run_id`` is present (guarded so DB
failures degrade gracefully). The two gate nodes pause the graph via
``interrupt()`` for human-in-the-loop decisions.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from langgraph.types import interrupt

from app.agents import ideator as ideator_agent
from app.agents import judge as judge_agent
from app.agents import literature as literature_agent
from app.agents import methodology as methodology_agent
from app.agents import plan as plan_agent
from app.db import repository
from app.db.models import MethodologyInput, PaperInput, QuestionInput, ScoreInput
from app.graph import deps
from app.graph.guards import check_budget, enforce_budget
from app.graph.state import (
    FEASIBILITY_RUBRIC,
    CostUsed,
    CriterionScore,
    MethodologyItem,
    PaperItem,
    PlanItem,
    QuestionItem,
    RankedPlanItem,
    ResearchState,
)
from app.llm import Usage
from app.logging import get_logger

log = get_logger(__name__)


def _selected(state: ResearchState) -> list[QuestionItem]:
    return [q for q in state.get("questions", []) if q.selected]


def _run_uuid(state: ResearchState) -> UUID | None:
    run_id = state.get("run_id")
    if not run_id:
        return None
    try:
        return UUID(str(run_id))
    except (ValueError, TypeError):
        return None


def _over_budget(state: ResearchState, cost: CostUsed) -> str | None:
    return check_budget({**state, "cost": cost})


# ---------------------------------------------------------------------------
# 1. Ideator
# ---------------------------------------------------------------------------


async def ideator(state: ResearchState) -> dict[str, Any]:
    capped = enforce_budget(state)
    if capped:
        return capped

    n = state["caps"].max_questions
    items, usage = await ideator_agent.generate_questions(
        state.get("brief", ""),
        state.get("researcher_context", ""),
        state.get("own_data", ""),
        n,
        invoke=deps.invoke,
    )

    run_id = _run_uuid(state)
    if run_id:
        try:
            db_qs = await repository.insert_questions(
                run_id,
                [
                    QuestionInput(text=q.text, rationale=q.rationale, tag=q.tag)
                    for q in items
                ],
            )
            items = [
                QuestionItem(
                    id=str(d.id),
                    text=d.text,
                    rationale=d.rationale or "",
                    tag=d.tag or "",
                )
                for d in db_qs
            ]
        except Exception:  # noqa: BLE001
            log.error("ideator_persist_failed", exc_info=True)

    log.info("ideator", count=len(items))
    return {
        "questions": items,
        "cost": state["cost"].bump(tokens=usage.total_tokens, cost=usage.cost_usd),
        "status": "ideating",
        "logs": [f"ideator: generated {len(items)} candidate questions"],
    }


# ---------------------------------------------------------------------------
# HITL gate 1: question selection / editing
# ---------------------------------------------------------------------------


async def gate_questions(state: ResearchState) -> dict[str, Any]:
    questions = state.get("questions", [])
    resume: Any = interrupt(
        {
            "gate": "question_selection",
            "questions": [q.model_dump() for q in questions],
        }
    )

    selected_ids: set[str] | None = None
    edited: dict[str, dict] = {}
    if isinstance(resume, dict):
        if resume.get("selected_ids") is not None:
            selected_ids = set(resume["selected_ids"])
        elif resume.get("selected_indexes") is not None:
            idxs = set(resume["selected_indexes"])
            selected_ids = {q.id for i, q in enumerate(questions) if i in idxs}
        for e in resume.get("edits", []) or []:
            if "id" in e:
                edited[e["id"]] = e

    updated: list[QuestionItem] = []
    for q in questions:
        data = q.model_dump()
        if q.id in edited:
            data.update({k: v for k, v in edited[q.id].items() if k != "id"})
        data["selected"] = q.id in selected_ids if selected_ids is not None else True
        updated.append(QuestionItem(**data))

    run_id = _run_uuid(state)
    if run_id:
        try:
            await repository.set_selected_questions(
                run_id, [UUID(q.id) for q in updated if q.selected]
            )
        except Exception:  # noqa: BLE001
            log.error("gate_questions_persist_failed", exc_info=True)

    n_selected = sum(1 for q in updated if q.selected)
    log.info("gate_questions", selected=n_selected)
    return {
        "questions": updated,
        "status": "reviewing_literature",
        "logs": [f"gate_questions: {n_selected} question(s) selected"],
    }


# ---------------------------------------------------------------------------
# 2. Literature review (plan -> act -> observe loop)
# ---------------------------------------------------------------------------


async def literature_review(state: ResearchState) -> dict[str, Any]:
    capped = enforce_budget(state)
    if capped:
        return capped

    cost = state["cost"]
    caps = state["caps"]
    run_id = _run_uuid(state)
    sources = state.get("sources")
    papers_by_question: dict[str, list[PaperItem]] = {}
    source_health: dict[str, str] = {}
    breached: str | None = None

    for q in _selected(state):
        try:
            outcome = await literature_agent.review_question(
                q.text,
                max_papers=caps.max_papers_per_question,
                sources=sources,
                invoke=deps.invoke,
                search=deps.search,
            )
        except Exception:  # noqa: BLE001 - degrade per-question
            log.error("literature_review_failed", question_id=q.id, exc_info=True)
            papers_by_question[q.id] = []
            continue

        papers_by_question[q.id] = outcome.papers
        for src, reason in outcome.source_health.items():
            source_health.setdefault(src, reason)
        cost = cost.bump(
            tokens=outcome.usage.total_tokens,
            cost=outcome.usage.cost_usd,
            tool_calls=outcome.tool_calls,
        )

        if run_id:
            try:
                await repository.insert_papers(
                    UUID(q.id),
                    [
                        PaperInput(
                            source=p.source,
                            title=p.title,
                            authors=p.authors,
                            year=p.year,
                            venue=p.venue,
                            doi=p.doi,
                            url=p.url,
                            abstract=p.abstract,
                            relevance=p.relevance,
                        )
                        for p in outcome.papers
                    ],
                )
            except Exception:  # noqa: BLE001
                log.error("papers_persist_failed", question_id=q.id, exc_info=True)

        breached = _over_budget(state, cost)
        if breached:
            break

    log.info(
        "literature_review",
        questions=len(papers_by_question),
        degraded_sources=sorted(source_health),
    )
    logs = [
        f"literature_review: gathered papers for {len(papers_by_question)} question(s)"
    ]
    for src, reason in source_health.items():
        logs.append(f"literature: {src} unavailable — {reason}")
    update: dict[str, Any] = {
        "papers_by_question": papers_by_question,
        "cost": cost,
        "source_health": source_health,
        "logs": logs,
    }
    if breached:
        update["status"] = "capped"
        update["capped_reason"] = breached
        update["logs"].append(f"budget: capped run ({breached})")
    else:
        update["status"] = "reviewing_literature"
    return update


# ---------------------------------------------------------------------------
# 3. Methodology
# ---------------------------------------------------------------------------


async def methodology(state: ResearchState) -> dict[str, Any]:
    capped = enforce_budget(state)
    if capped:
        return capped

    cost = state["cost"]
    run_id = _run_uuid(state)
    papers_by_question = state.get("papers_by_question", {})
    methodologies: dict[str, MethodologyItem] = {}

    for q in _selected(state):
        try:
            item, usage = await methodology_agent.synthesize(
                q.text,
                papers_by_question.get(q.id, []),
                state.get("own_data", ""),
                invoke=deps.invoke,
            )
        except Exception:  # noqa: BLE001
            log.error("methodology_failed", question_id=q.id, exc_info=True)
            item = MethodologyItem(gaps=["methodology synthesis failed"])
            usage = Usage()

        methodologies[q.id] = item
        cost = cost.bump(tokens=usage.total_tokens, cost=usage.cost_usd)

        if run_id:
            try:
                await repository.upsert_methodology(
                    UUID(q.id),
                    MethodologyInput(
                        methods=item.methods, datasets=item.datasets, gaps=item.gaps
                    ),
                )
            except Exception:  # noqa: BLE001
                log.error("methodology_persist_failed", question_id=q.id, exc_info=True)

    log.info("methodology", count=len(methodologies))
    return {
        "methodologies": methodologies,
        "cost": cost,
        "status": "designing_methodology",
        "logs": [f"methodology: synthesized for {len(methodologies)} question(s)"],
    }


# ---------------------------------------------------------------------------
# 4. Research plan
# ---------------------------------------------------------------------------


async def research_plan(state: ResearchState) -> dict[str, Any]:
    capped = enforce_budget(state)
    if capped:
        return capped

    cost = state["cost"]
    run_id = _run_uuid(state)
    methodologies = state.get("methodologies", {})
    papers_by_question = state.get("papers_by_question", {})
    plans: list[PlanItem] = []

    for q in _selected(state):
        try:
            content, usage = await plan_agent.draft_plan(
                q.text,
                methodologies.get(q.id),
                papers_by_question.get(q.id, []),
                invoke=deps.invoke,
            )
        except Exception:  # noqa: BLE001
            log.error("plan_failed", question_id=q.id, exc_info=True)
            content = {"objective": "plan drafting failed", "error": True}
            usage = Usage()

        plan_item = PlanItem(question_id=q.id, content=content)
        cost = cost.bump(tokens=usage.total_tokens, cost=usage.cost_usd)

        if run_id:
            try:
                db_plan = await repository.insert_plan(UUID(q.id), content)
                plan_item = PlanItem(
                    id=str(db_plan.id), question_id=q.id, content=content
                )
            except Exception:  # noqa: BLE001
                log.error("plan_persist_failed", question_id=q.id, exc_info=True)

        plans.append(plan_item)

    log.info("research_plan", count=len(plans))
    return {
        "plans": plans,
        "cost": cost,
        "status": "planning",
        "logs": [f"research_plan: drafted {len(plans)} plan(s)"],
    }


# ---------------------------------------------------------------------------
# 5. Judge (rubric scoring + ranking)
# ---------------------------------------------------------------------------


async def judge(state: ResearchState) -> dict[str, Any]:
    capped = enforce_budget(state)
    if capped:
        return capped

    cost = state["cost"]
    run_id = _run_uuid(state)
    questions_by_id = {q.id: q for q in state.get("questions", [])}
    ranked: list[RankedPlanItem] = []

    for plan in state.get("plans", []):
        question_text = ""
        q = questions_by_id.get(plan.question_id)
        if q:
            question_text = q.text
        try:
            scores, usage = await judge_agent.evaluate_plan(
                question_text, plan.content, invoke=deps.invoke
            )
        except Exception:  # noqa: BLE001
            log.error("judge_failed", plan_id=plan.id, exc_info=True)
            scores = [
                CriterionScore(criterion=c, score=0.0, weight=w, justification="failed")
                for c, w in FEASIBILITY_RUBRIC.items()
            ]
            usage = Usage()

        total = sum(s.score * s.weight for s in scores)
        ranked.append(RankedPlanItem(plan=plan, scores=scores, total=total))
        cost = cost.bump(tokens=usage.total_tokens, cost=usage.cost_usd)

    ranked.sort(key=lambda r: r.total, reverse=True)
    for i, r in enumerate(ranked):
        r.rank = i + 1

    if run_id:
        for r in ranked:
            try:
                await repository.insert_scores(
                    UUID(r.plan.id),
                    [
                        ScoreInput(
                            criterion=s.criterion,
                            score=s.score,
                            weight=s.weight,
                            justification=s.justification,
                            total=r.total,
                        )
                        for s in r.scores
                    ],
                )
                await repository.set_plan_ranking(UUID(r.plan.id), r.total, r.rank)
            except Exception:  # noqa: BLE001
                log.error("judge_persist_failed", plan_id=r.plan.id, exc_info=True)

    log.info("judge", ranked=len(ranked))
    return {
        "ranked_plans": ranked,
        "cost": cost,
        "status": "judging",
        "logs": [f"judge: scored and ranked {len(ranked)} plan(s)"],
    }


# ---------------------------------------------------------------------------
# HITL gate 2: plan approval (before Notion export)
# ---------------------------------------------------------------------------


async def gate_plan_approval(state: ResearchState) -> dict[str, Any]:
    ranked = state.get("ranked_plans", [])
    resume: Any = interrupt(
        {
            "gate": "plan_approval",
            "ranked_plans": [r.model_dump() for r in ranked],
        }
    )

    approved_plan_id: str | None = None
    if isinstance(resume, dict):
        if resume.get("approved_plan_id"):
            approved_plan_id = resume["approved_plan_id"]
        elif resume.get("approved_index") is not None:
            idx = resume["approved_index"]
            if 0 <= idx < len(ranked):
                approved_plan_id = ranked[idx].plan.id
    if approved_plan_id is None and ranked:
        approved_plan_id = ranked[0].plan.id

    log.info("gate_plan_approval", approved_plan_id=approved_plan_id)
    return {
        "approved_plan_id": approved_plan_id,
        "status": "completed",
        "logs": [f"gate_plan_approval: approved plan {approved_plan_id}"],
    }
