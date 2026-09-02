from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from platform_runtime.application.lifecycle import WindowCloseMode
from platform_runtime.domain.events import EventKind, RuntimeEvent
from platform_runtime.domain.job import JobSnapshot, JobStatus, RuntimeSnapshot


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    active_job_id: str | None
    window_close_mode: WindowCloseMode


class JobResponse(BaseModel):
    id: str
    kind: str
    status: JobStatus
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime


class StartJobRequest(BaseModel):
    """Body for ``POST /jobs/start``.

    ``kind`` defaults to ``demo_long_task`` when omitted, so existing
    callers that post an empty body keep working.
    """

    kind: str = "demo_long_task"
    input: dict[str, Any] = {}


class EventResponse(BaseModel):
    sequence: int
    event_id: str
    job_id: str
    kind: EventKind
    status: JobStatus
    progress: int
    message: str
    created_at: datetime


class SnapshotResponse(BaseModel):
    job: JobResponse | None
    events: list[EventResponse]
    event_cursor: int


class CalcPressRequest(BaseModel):
    """Body for ``POST /calc/press`` — a single calculator key string."""

    key: str


class CalcHistoryItem(BaseModel):
    expression: str
    result: str


class CalcStateResponse(BaseModel):
    display: str
    expression: list[str]
    error: bool
    memory: list[str]
    history: list[CalcHistoryItem]


def calc_state_response(view: dict[str, Any]) -> CalcStateResponse:
    return CalcStateResponse(
        display=view["display"],
        expression=list(view["expression"]),
        error=bool(view["error"]),
        memory=list(view["memory"]),
        history=[CalcHistoryItem(**item) for item in view["history"]],
    )


def job_response(job: JobSnapshot | None) -> JobResponse | None:
    if job is None:
        return None
    return JobResponse(
        id=job.job_id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def event_response(event: RuntimeEvent) -> EventResponse:
    return EventResponse(
        sequence=event.sequence,
        event_id=event.event_id,
        job_id=event.job_id,
        kind=event.kind,
        status=event.status,
        progress=event.progress,
        message=event.message,
        created_at=event.created_at,
    )


def snapshot_response(snapshot: RuntimeSnapshot) -> SnapshotResponse:
    return SnapshotResponse(
        job=job_response(snapshot.job),
        events=[event_response(event) for event in snapshot.events],
        event_cursor=snapshot.event_cursor,
    )