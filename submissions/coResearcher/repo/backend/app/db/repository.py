"""Typed data-access helpers over the psycopg async pool.

Every function returns validated Pydantic models (or lists thereof). JSONB
columns are wrapped with ``Jsonb`` on write and arrive as native Python objects
on read (psycopg registers JSON loaders by default).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.db.models import (
    Methodology,
    MethodologyInput,
    Paper,
    PaperInput,
    Plan,
    Project,
    Question,
    QuestionInput,
    RankedPlan,
    Run,
    RunResults,
    RunStatus,
    Score,
    ScoreInput,
)
from app.db.pool import get_pool

# --- projects ---------------------------------------------------------------


async def create_project(
    brief: str,
    researcher_context: str | None = None,
    own_data: str | None = None,
) -> Project:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            insert into projects (brief, researcher_context, own_data)
            values (%s, %s, %s)
            returning *
            """,
            (brief, researcher_context, own_data),
        )
        return Project.model_validate(await cur.fetchone())


async def get_project(project_id: UUID) -> Project | None:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("select * from projects where id = %s", (project_id,))
        row = await cur.fetchone()
        return Project.model_validate(row) if row else None


# --- runs -------------------------------------------------------------------


async def create_run(
    project_id: UUID,
    thread_id: str,
    caps: dict[str, Any] | None = None,
    status: RunStatus = "pending",
) -> Run:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            insert into runs (project_id, thread_id, caps, status)
            values (%s, %s, %s, %s)
            returning *
            """,
            (project_id, thread_id, Jsonb(caps or {}), status),
        )
        return Run.model_validate(await cur.fetchone())


async def get_run(run_id: UUID) -> Run | None:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("select * from runs where id = %s", (run_id,))
        row = await cur.fetchone()
        return Run.model_validate(row) if row else None


async def get_run_by_thread(thread_id: str) -> Run | None:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("select * from runs where thread_id = %s", (thread_id,))
        row = await cur.fetchone()
        return Run.model_validate(row) if row else None


async def update_run_status(
    run_id: UUID, status: RunStatus, error: str | None = None
) -> Run | None:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "update runs set status = %s, error = %s where id = %s returning *",
            (status, error, run_id),
        )
        row = await cur.fetchone()
        return Run.model_validate(row) if row else None


async def update_run_cost(run_id: UUID, cost_used: dict[str, Any]) -> Run | None:
    """Merge new cost metrics into the existing ``cost_used`` JSONB."""
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "update runs set cost_used = cost_used || %s where id = %s returning *",
            (Jsonb(cost_used), run_id),
        )
        row = await cur.fetchone()
        return Run.model_validate(row) if row else None


# --- questions --------------------------------------------------------------


async def insert_questions(
    run_id: UUID, questions: list[QuestionInput]
) -> list[Question]:
    if not questions:
        return []
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        rows: list[dict[str, Any]] = []
        for i, q in enumerate(questions):
            await cur.execute(
                """
                insert into questions (run_id, text, rationale, tag, selected, position)
                values (%s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    run_id,
                    q.text,
                    q.rationale,
                    q.tag,
                    q.selected,
                    q.position or i,
                ),
            )
            rows.append(await cur.fetchone())
        return [Question.model_validate(r) for r in rows]


async def get_questions(run_id: UUID, *, selected_only: bool = False) -> list[Question]:
    sql = "select * from questions where run_id = %s"
    if selected_only:
        sql += " and selected = true"
    sql += " order by position asc, created_at asc"
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, (run_id,))
        return [Question.model_validate(r) for r in await cur.fetchall()]


async def set_selected_questions(run_id: UUID, selected_ids: list[UUID]) -> None:
    """Mark the given question ids selected and all others in the run unselected."""
    async with get_pool().connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "update questions set selected = (id = any(%s)) where run_id = %s",
            (list(selected_ids), run_id),
        )


# --- papers -----------------------------------------------------------------


async def insert_papers(question_id: UUID, papers: list[PaperInput]) -> list[Paper]:
    if not papers:
        return []
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        rows: list[dict[str, Any]] = []
        for p in papers:
            await cur.execute(
                """
                insert into papers
                    (question_id, source, title, authors, year, venue, doi, url,
                     abstract, relevance)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    question_id,
                    p.source,
                    p.title,
                    Jsonb(p.authors),
                    p.year,
                    p.venue,
                    p.doi,
                    p.url,
                    p.abstract,
                    p.relevance,
                ),
            )
            rows.append(await cur.fetchone())
        return [Paper.model_validate(r) for r in rows]


async def get_question(question_id: UUID) -> Question | None:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("select * from questions where id = %s", (question_id,))
        row = await cur.fetchone()
        return Question.model_validate(row) if row else None


async def get_papers_for_question(question_id: UUID) -> list[Paper]:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "select * from papers where question_id = %s order by created_at asc",
            (question_id,),
        )
        return [Paper.model_validate(r) for r in await cur.fetchall()]


async def get_papers_for_run(run_id: UUID) -> list[Paper]:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            select p.* from papers p
            join questions q on q.id = p.question_id
            where q.run_id = %s
            order by p.created_at asc
            """,
            (run_id,),
        )
        return [Paper.model_validate(r) for r in await cur.fetchall()]


# --- methodologies ----------------------------------------------------------


async def upsert_methodology(
    question_id: UUID, methodology: MethodologyInput
) -> Methodology:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            insert into methodologies (question_id, methods, datasets, gaps)
            values (%s, %s, %s, %s)
            on conflict (question_id) do update set
                methods = excluded.methods,
                datasets = excluded.datasets,
                gaps = excluded.gaps
            returning *
            """,
            (
                question_id,
                Jsonb(methodology.methods),
                Jsonb(methodology.datasets),
                Jsonb(methodology.gaps),
            ),
        )
        return Methodology.model_validate(await cur.fetchone())


async def get_methodologies_for_run(run_id: UUID) -> list[Methodology]:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            select m.* from methodologies m
            join questions q on q.id = m.question_id
            where q.run_id = %s
            """,
            (run_id,),
        )
        return [Methodology.model_validate(r) for r in await cur.fetchall()]


# --- plans ------------------------------------------------------------------


async def insert_plan(question_id: UUID, content_json: dict[str, Any]) -> Plan:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            insert into plans (question_id, content_json)
            values (%s, %s)
            returning *
            """,
            (question_id, Jsonb(content_json)),
        )
        return Plan.model_validate(await cur.fetchone())


async def set_plan_ranking(
    plan_id: UUID, feasibility_total: float, rank: int
) -> Plan | None:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            update plans set feasibility_total = %s, rank = %s
            where id = %s returning *
            """,
            (feasibility_total, rank, plan_id),
        )
        row = await cur.fetchone()
        return Plan.model_validate(row) if row else None


async def set_plan_notion_url(plan_id: UUID, notion_url: str) -> Plan | None:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "update plans set notion_url = %s where id = %s returning *",
            (notion_url, plan_id),
        )
        row = await cur.fetchone()
        return Plan.model_validate(row) if row else None


async def get_plan(plan_id: UUID) -> Plan | None:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("select * from plans where id = %s", (plan_id,))
        row = await cur.fetchone()
        return Plan.model_validate(row) if row else None


async def get_plans_for_run(run_id: UUID) -> list[Plan]:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            select p.* from plans p
            join questions q on q.id = p.question_id
            where q.run_id = %s
            order by p.rank asc nulls last, p.created_at asc
            """,
            (run_id,),
        )
        return [Plan.model_validate(r) for r in await cur.fetchall()]


# --- scores -----------------------------------------------------------------


async def insert_scores(plan_id: UUID, scores: list[ScoreInput]) -> list[Score]:
    if not scores:
        return []
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        rows: list[dict[str, Any]] = []
        for s in scores:
            await cur.execute(
                """
                insert into scores
                    (plan_id, criterion, score, weight, justification, total)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (plan_id, criterion) do update set
                    score = excluded.score,
                    weight = excluded.weight,
                    justification = excluded.justification,
                    total = excluded.total
                returning *
                """,
                (
                    plan_id,
                    s.criterion,
                    s.score,
                    s.weight,
                    s.justification,
                    s.total,
                ),
            )
            rows.append(await cur.fetchone())
        return [Score.model_validate(r) for r in rows]


async def get_scores_for_plan(plan_id: UUID) -> list[Score]:
    async with get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "select * from scores where plan_id = %s order by criterion asc",
            (plan_id,),
        )
        return [Score.model_validate(r) for r in await cur.fetchall()]


# --- aggregate --------------------------------------------------------------


async def get_run_results(run_id: UUID) -> RunResults | None:
    """Assemble the full result view for a run."""
    run = await get_run(run_id)
    if run is None:
        return None
    project = await get_project(run.project_id)
    if project is None:
        return None

    questions = await get_questions(run_id)
    papers = await get_papers_for_run(run_id)
    methodologies = await get_methodologies_for_run(run_id)
    plans = await get_plans_for_run(run_id)

    ranked_plans: list[RankedPlan] = []
    for plan in plans:
        scores = await get_scores_for_plan(plan.id)
        ranked_plans.append(RankedPlan(plan=plan, scores=scores))

    return RunResults(
        run=run,
        project=project,
        questions=questions,
        papers=papers,
        methodologies=methodologies,
        ranked_plans=ranked_plans,
    )
