from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {
            JobStatus.COMPLETED,
            JobStatus.CANCELLED,
            JobStatus.FAILED,
        }


@dataclass(frozen=True, slots=True)
class JobSnapshot:
    job_id: str
    kind: str
    status: JobStatus
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    job: JobSnapshot | None
    events: tuple["RuntimeEvent", ...]
    event_cursor: int