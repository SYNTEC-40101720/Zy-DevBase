from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .job import JobStatus


class EventKind(StrEnum):
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    PROGRESS = "progress"
    JOB_COMPLETED = "job_completed"
    JOB_CANCELLED = "job_cancelled"
    JOB_FAILED = "job_failed"

    @property
    def is_progress(self) -> bool:
        return self is EventKind.PROGRESS


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    sequence: int
    event_id: str
    job_id: str
    kind: EventKind
    status: JobStatus
    progress: int
    message: str
    created_at: datetime

    @property
    def is_critical(self) -> bool:
        return not self.kind.is_progress