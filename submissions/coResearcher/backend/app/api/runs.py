"""Runs API: create, stream (SSE), resume (HITL), and fetch results."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    CapsOverride,
    CreateRunRequest,
    CreateRunResponse,
    ExportRequest,
    ExportResponse,
    ResumeRequest,
    RunAcceptedResponse,
)
from app.db import repository
from app.db.models import RunResults
from app.graph.state import initial_state
from app.logging import get_logger
from app.notion import (
    ExportNotApprovedError,
    ExportPlanMismatchError,
    ExportPlanNotFoundError,
    NotionExporter,
    NotionExportError,
    export_plan,
)
from app.run_manager import TERMINAL_EVENTS, RunAlreadyActiveError, RunManager

log = get_logger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])

_TIMEOUT_BUFFER_SECONDS = 60


def _manager(request: Request) -> RunManager:
    manager = getattr(request.app.state, "run_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Service not ready (no database).")
    return manager


def _parse_uuid(run_id: str) -> UUID:
    try:
        return UUID(run_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid run id.") from exc


@router.post("", response_model=CreateRunResponse, status_code=201)
async def create_run(request: Request, body: CreateRunRequest) -> CreateRunResponse:
    manager = _manager(request)
    caps = (body.caps or CapsOverride()).merged()

    project = await repository.create_project(
        body.brief, body.researcher_context, body.own_data
    )
    thread_id = str(uuid4())
    run = await repository.create_run(
        project.id, thread_id, caps=caps.model_dump(), status="pending"
    )

    state = initial_state(
        brief=body.brief,
        researcher_context=body.researcher_context,
        own_data=body.own_data,
        caps=caps,
        run_id=str(run.id),
        thread_id=thread_id,
        sources=body.sources,
    )
    await manager.start(
        str(run.id),
        thread_id,
        state,
        timeout=caps.wall_clock_seconds + _TIMEOUT_BUFFER_SECONDS,
    )
    log.info("run_created", run_id=str(run.id))
    return CreateRunResponse(run_id=str(run.id), thread_id=thread_id, status=run.status)


@router.get("/{run_id}/stream")
async def stream_run(request: Request, run_id: str):
    manager = _manager(request)
    rid = _parse_uuid(run_id)
    run = await repository.get_run(rid)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    async def event_generator():
        # Initial snapshot so late/reconnecting clients know the current state.
        snapshot = await manager.snapshot(run.thread_id)
        yield {"event": "snapshot", "data": json.dumps(snapshot, default=str)}

        if not manager.is_active(str(rid)):
            return  # nothing live to stream; snapshot reflects terminal/paused state

        queue = manager.subscribe(str(rid))
        try:
            while True:
                if await request.is_disconnected():
                    break
                event = await queue.get()
                yield {
                    "event": event.event,
                    "data": json.dumps(event.data, default=str),
                }
                if event.event in TERMINAL_EVENTS:
                    break
        finally:
            manager.unsubscribe(str(rid), queue)

    return EventSourceResponse(event_generator())


@router.post("/{run_id}/resume", response_model=RunAcceptedResponse, status_code=202)
async def resume_run(
    request: Request, run_id: str, body: ResumeRequest
) -> RunAcceptedResponse:
    manager = _manager(request)
    rid = _parse_uuid(run_id)
    run = await repository.get_run(rid)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    caps_seconds = int(run.caps.get("wall_clock_seconds", 900)) if run.caps else 900
    try:
        await manager.resume(
            str(rid),
            run.thread_id,
            body.resume,
            timeout=caps_seconds + _TIMEOUT_BUFFER_SECONDS,
        )
    except RunAlreadyActiveError as exc:
        raise HTTPException(status_code=409, detail="Run is already executing.") from exc

    return RunAcceptedResponse(run_id=str(rid), status="resuming")


@router.post("/{run_id}/export", response_model=ExportResponse)
async def export_run(
    request: Request, run_id: str, body: ExportRequest
) -> ExportResponse:
    rid = _parse_uuid(run_id)
    run = await repository.get_run(rid)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="Service not ready (no graph).")

    try:
        exporter = NotionExporter.from_settings()
    except NotionExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = await export_plan(
            run.thread_id,
            graph=graph,
            exporter=exporter,
            requested_plan_id=body.plan_id,
        )
    except ExportNotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ExportPlanMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExportPlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Approved plan not found.") from exc
    except NotionExportError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ExportResponse(**result)


@router.get("/{run_id}", response_model=RunResults)
async def get_run(run_id: str) -> RunResults:
    rid = _parse_uuid(run_id)
    results = await repository.get_run_results(rid)
    if results is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return results
