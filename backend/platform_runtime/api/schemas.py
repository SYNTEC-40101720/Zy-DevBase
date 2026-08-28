from datetime import datetime
from typing import Literal

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