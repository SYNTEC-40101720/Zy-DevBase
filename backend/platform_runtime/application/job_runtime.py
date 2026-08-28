from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event, RLock, Thread
from uuid import uuid4

from platform_runtime.domain.events import EventKind, RuntimeEvent
from platform_runtime.domain.job import JobSnapshot, JobStatus, RuntimeSnapshot

from .errors import (
    JobAlreadyRunningError,
    JobNotCancellableError,
    NoCurrentJobError,
)
from .event_bus import InMemoryEventBus


@dataclass(slots=True)
class _MutableJob:
    job_id: str
    kind: str
    status: JobStatus
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime
    cancellation_requested: Event


class JobRuntime:
    """Owns one in-memory demo job and its worker thread."""

    def __init__(
        self,
        event_bus: InMemoryEventBus | None = None,
        *,
        total_steps: int = 10,
        step_delay: float = 0.2,
    ) -> None:
        if total_steps < 1:
            raise ValueError("total_steps must be positive")
        if step_delay < 0:
            raise ValueError("step_delay must not be negative")
        self._event_bus = event_bus or InMemoryEventBus()
        self._total_steps = total_steps
        self._step_delay = step_delay
        self._lock = RLock()
        self._active: _MutableJob | None = None

    def start_demo(self) -> JobSnapshot:
        with self._lock:
            if self._active and not self._active.status.is_terminal:
                raise JobAlreadyRunningError("a non-terminal job is already running")

            now = _utc_now()
            job = _MutableJob(
                job_id=str(uuid4()),
                kind="demo_long_task",
                status=JobStatus.QUEUED,
                progress=0,
                message="演示任务已排队",
                created_at=now,
                updated_at=now,
                cancellation_requested=Event(),
            )
            self._active = job
            self._emit_locked(job, EventKind.JOB_CREATED)
            snapshot = self._snapshot_locked(job)

        Thread(
            target=self._run_demo,
            args=(job.job_id,),
            name=f"platform-demo-{job.job_id[:8]}",
            daemon=True,
        ).start()
        return snapshot

    def cancel_current(self) -> JobSnapshot:
        with self._lock:
            if self._active is None:
                raise NoCurrentJobError("no current job exists")
            if self._active.status.is_terminal:
                raise JobNotCancellableError("the current job is already terminal")

            self._active.cancellation_requested.set()
            self._set_state_locked(
                self._active,
                status=JobStatus.CANCELLED,
                kind=EventKind.JOB_CANCELLED,
                message="任务已取消",
            )
            return self._snapshot_locked(self._active)

    def current_job(self) -> JobSnapshot | None:
        with self._lock:
            if self._active is None:
                return None
            return self._snapshot_locked(self._active)

    def current_snapshot(self, after_sequence: int = 0) -> RuntimeSnapshot:
        with self._lock:
            job = (
                None
                if self._active is None
                else self._snapshot_locked(self._active)
            )
            event_snapshot = self._event_bus.snapshot(after_sequence)
            return RuntimeSnapshot(
                job=job,
                events=event_snapshot.events,
                event_cursor=event_snapshot.cursor,
            )

    def wait_for_events(
        self,
        after_sequence: int,
        timeout: float | None = None,
    ) -> tuple[RuntimeEvent, ...]:
        return self._event_bus.wait_for_events(after_sequence, timeout)

    def _run_demo(self, job_id: str) -> None:
        try:
            with self._lock:
                job = self._get_active_locked(job_id)
                if job is None or job.status.is_terminal:
                    return
                self._set_state_locked(
                    job,
                    status=JobStatus.RUNNING,
                    kind=EventKind.JOB_STARTED,
                    message="演示任务运行中",
                )

            for step in range(1, self._total_steps + 1):
                if job.cancellation_requested.wait(self._step_delay):
                    return
                with self._lock:
                    job = self._get_active_locked(job_id)
                    if (
                        job is None
                        or job.status.is_terminal
                        or job.cancellation_requested.is_set()
                    ):
                        return
                    self._set_state_locked(
                        job,
                        status=JobStatus.RUNNING,
                        kind=EventKind.PROGRESS,
                        progress=round(step * 100 / self._total_steps),
                        message=f"演示任务进度 {step}/{self._total_steps}",
                    )

            with self._lock:
                job = self._get_active_locked(job_id)
                if job is not None and not job.status.is_terminal:
                    self._set_state_locked(
                        job,
                        status=JobStatus.COMPLETED,
                        kind=EventKind.JOB_COMPLETED,
                        progress=100,
                        message="演示任务已完成",
                    )
        except Exception as exc:
            with self._lock:
                job = self._get_active_locked(job_id)
                if job is not None and not job.status.is_terminal:
                    self._set_state_locked(
                        job,
                        status=JobStatus.FAILED,
                        kind=EventKind.JOB_FAILED,
                        message=f"演示任务失败: {exc}",
                    )

    def _get_active_locked(self, job_id: str) -> _MutableJob | None:
        if self._active is None or self._active.job_id != job_id:
            return None
        return self._active

    def _set_state_locked(
        self,
        job: _MutableJob,
        *,
        status: JobStatus,
        kind: EventKind,
        message: str,
        progress: int | None = None,
    ) -> None:
        job.status = status
        job.message = message
        if progress is not None:
            job.progress = progress
        job.updated_at = _utc_now()
        self._emit_locked(job, kind)

    def _emit_locked(self, job: _MutableJob, kind: EventKind) -> None:
        self._event_bus.publish(
            RuntimeEvent(
                sequence=0,
                event_id=str(uuid4()),
                job_id=job.job_id,
                kind=kind,
                status=job.status,
                progress=job.progress,
                message=job.message,
                created_at=job.updated_at,
            )
        )

    @staticmethod
    def _snapshot_locked(job: _MutableJob) -> JobSnapshot:
        return JobSnapshot(
            job_id=job.job_id,
            kind=job.kind,
            status=job.status,
            progress=job.progress,
            message=job.message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)