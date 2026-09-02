from time import monotonic, sleep

import pytest

from zy_devbase.application.errors import JobAlreadyRunningError
from zy_devbase.application.event_bus import InMemoryEventBus
from zy_devbase.application.job_runtime import JobRuntime
from zy_devbase.application.lifecycle import (
    LifecyclePolicy,
    WindowCloseMode,
    WindowLifecycle,
)
from zy_devbase.domain.events import EventKind, RuntimeEvent
from zy_devbase.domain.job import JobStatus


def wait_for_status(runtime: JobRuntime, expected: JobStatus) -> None:
    deadline = monotonic() + 2
    while monotonic() < deadline:
        job = runtime.current_job()
        if job is not None and job.status is expected:
            return
        sleep(0.005)
    raise AssertionError(f"job did not reach {expected}")


def test_demo_job_completes_and_keeps_lifecycle_events() -> None:
    runtime = JobRuntime(total_steps=4, step_delay=0.005)

    started = runtime.start_demo()
    wait_for_status(runtime, JobStatus.COMPLETED)

    snapshot = runtime.current_snapshot()
    assert snapshot.job is not None
    assert snapshot.job.job_id == started.job_id
    assert snapshot.job.progress == 100
    assert snapshot.job.status is JobStatus.COMPLETED
    kinds = [event.kind for event in snapshot.events]
    assert kinds[0] is EventKind.JOB_CREATED
    assert EventKind.JOB_STARTED in kinds
    assert EventKind.JOB_COMPLETED in kinds


def test_demo_job_can_be_cancelled() -> None:
    runtime = JobRuntime(total_steps=100, step_delay=0.02)

    runtime.start_demo()
    cancelled = runtime.cancel_current()

    assert cancelled.status is JobStatus.CANCELLED
    wait_for_status(runtime, JobStatus.CANCELLED)
    assert runtime.current_snapshot().events[-1].kind is EventKind.JOB_CANCELLED


def test_second_non_terminal_job_is_rejected() -> None:
    runtime = JobRuntime(total_steps=100, step_delay=0.02)

    runtime.start_demo()
    with pytest.raises(JobAlreadyRunningError):
        runtime.start_demo()
    runtime.cancel_current()


def test_event_bus_merges_progress_but_retains_key_events() -> None:
    bus = InMemoryEventBus()

    def event(kind: EventKind, progress: int) -> RuntimeEvent:
        from datetime import datetime, timezone

        return RuntimeEvent(
            sequence=0,
            event_id=f"{kind}-{progress}",
            job_id="job-1",
            kind=kind,
            status=(
                JobStatus.RUNNING
                if kind is not EventKind.JOB_COMPLETED
                else JobStatus.COMPLETED
            ),
            progress=progress,
            message=kind.value,
            created_at=datetime.now(timezone.utc),
        )

    bus.publish(event(EventKind.JOB_STARTED, 0))
    bus.publish(event(EventKind.PROGRESS, 25))
    bus.publish(event(EventKind.PROGRESS, 75))
    bus.publish(event(EventKind.JOB_COMPLETED, 100))

    snapshot = bus.snapshot()
    assert [item.kind for item in snapshot.events] == [
        EventKind.JOB_STARTED,
        EventKind.PROGRESS,
        EventKind.JOB_COMPLETED,
    ]
    assert snapshot.events[1].progress == 75


def test_event_bus_history_has_a_configurable_bound() -> None:
    bus = InMemoryEventBus(history_size=2)

    def event(kind: EventKind, progress: int) -> RuntimeEvent:
        from datetime import datetime, timezone

        return RuntimeEvent(
            sequence=0,
            event_id=f"{kind}-{progress}",
            job_id="job-1",
            kind=kind,
            status=JobStatus.RUNNING,
            progress=progress,
            message=kind.value,
            created_at=datetime.now(timezone.utc),
        )

    bus.publish(event(EventKind.JOB_CREATED, 0))
    bus.publish(event(EventKind.JOB_STARTED, 0))
    bus.publish(event(EventKind.PROGRESS, 50))

    snapshot = bus.snapshot()
    assert len(snapshot.events) == 2
    assert snapshot.cursor == 3
    assert [item.kind for item in snapshot.events] == [
        EventKind.JOB_STARTED,
        EventKind.PROGRESS,
    ]


def test_window_lifecycle_is_explicit_and_injected() -> None:
    calls: list[str] = []
    lifecycle = WindowLifecycle(
        LifecyclePolicy(WindowCloseMode.STOP_ON_CLOSE),
        stop_active_job=lambda: calls.append("stop") is None,
    )

    result = lifecycle.handle_window_close()

    assert result.mode is WindowCloseMode.STOP_ON_CLOSE
    assert result.stop_requested is True
    assert calls == ["stop"]
    assert (
        WindowLifecycle().handle_window_close().mode
        is WindowCloseMode.CONTINUE_ON_CLOSE
    )