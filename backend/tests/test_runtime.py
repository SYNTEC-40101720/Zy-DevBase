from time import monotonic, sleep

import pytest

from devbase.application.errors import JobAlreadyRunningError
from devbase.application.event_bus import InMemoryEventBus
from devbase.application.job_runtime import JobRuntime
from devbase.application.lifecycle import (
    LifecyclePolicy,
    WindowCloseMode,
    WindowLifecycle,
)
from devbase.domain.events import EventKind, RuntimeEvent
from devbase.domain.job import JobPhase, JobStatus, JobTrigger


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
    wait_for_status(runtime, JobStatus.SUCCEEDED)

    snapshot = runtime.current_snapshot()
    assert snapshot.job is not None
    assert snapshot.job.job_id == started.job_id
    assert snapshot.job.progress == 100
    assert snapshot.job.status is JobStatus.SUCCEEDED
    kinds = [event.kind for event in snapshot.events]
    assert kinds[0] is EventKind.JOB_CREATED
    assert EventKind.JOB_STARTED in kinds
    assert EventKind.JOB_SUCCEEDED in kinds


def test_demo_job_can_be_cancelled() -> None:
    runtime = JobRuntime(total_steps=100, step_delay=0.02)

    runtime.start_demo()
    cancelled = runtime.cancel_current()

    assert cancelled.status is JobStatus.CANCELLING
    wait_for_status(runtime, JobStatus.CANCELLED)
    # CANCELLING event emitted at cancel time
    events = runtime.current_snapshot().events
    assert any(e.kind is EventKind.JOB_CANCELLING for e in events)
    # Final event is CANCELLED after worker observes cancel
    assert events[-1].kind is EventKind.JOB_CANCELLED


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
                if kind is not EventKind.JOB_SUCCEEDED
                else JobStatus.SUCCEEDED
            ),
            progress=progress,
            message=kind.value,
            created_at=datetime.now(timezone.utc),
        )

    bus.publish(event(EventKind.JOB_STARTED, 0))
    bus.publish(event(EventKind.PROGRESS, 25))
    bus.publish(event(EventKind.PROGRESS, 75))
    bus.publish(event(EventKind.JOB_SUCCEEDED, 100))

    snapshot = bus.snapshot()
    assert [item.kind for item in snapshot.events] == [
        EventKind.JOB_STARTED,
        EventKind.PROGRESS,
        EventKind.JOB_SUCCEEDED,
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


# ---------------------------------------------------------------------------
# 任务 4：状态机统一 — JobStatus / JobPhase / JobTrigger
# ---------------------------------------------------------------------------

class TestJobStateMachine:
    def test_all_required_statuses_exist(self) -> None:
        for name in (
            "QUEUED",
            "RUNNING",
            "CANCELLING",
            "SUCCEEDED",
            "COMPLETED_WITH_WARNINGS",
            "CANCELLED",
            "FAILED",
        ):
            assert hasattr(JobStatus, name), f"missing JobStatus.{name}"

    def test_terminal_statuses(self) -> None:
        assert JobStatus.SUCCEEDED.is_terminal
        assert JobStatus.COMPLETED_WITH_WARNINGS.is_terminal
        assert JobStatus.CANCELLED.is_terminal
        assert JobStatus.FAILED.is_terminal

    def test_non_terminal_statuses(self) -> None:
        assert not JobStatus.QUEUED.is_terminal
        assert not JobStatus.RUNNING.is_terminal
        assert not JobStatus.CANCELLING.is_terminal

    def test_active_statuses(self) -> None:
        assert JobStatus.QUEUED.is_active
        assert JobStatus.RUNNING.is_active
        assert JobStatus.CANCELLING.is_active
        assert not JobStatus.SUCCEEDED.is_active
        assert not JobStatus.CANCELLED.is_active


class TestJobPhase:
    def test_pending_matches_queued(self) -> None:
        assert JobPhase.PENDING.matches(JobStatus.QUEUED)
        assert not JobPhase.PENDING.matches(JobStatus.RUNNING)

    def test_executing_matches_running_and_cancelling(self) -> None:
        assert JobPhase.EXECUTING.matches(JobStatus.RUNNING)
        assert JobPhase.EXECUTING.matches(JobStatus.CANCELLING)
        assert not JobPhase.EXECUTING.matches(JobStatus.QUEUED)

    def test_done_matches_all_terminal(self) -> None:
        for status in (
            JobStatus.SUCCEEDED,
            JobStatus.COMPLETED_WITH_WARNINGS,
            JobStatus.CANCELLED,
            JobStatus.FAILED,
        ):
            assert JobPhase.DONE.matches(status)


class TestJobTrigger:
    def test_values(self) -> None:
        assert JobTrigger.USER.value == "user"
        assert JobTrigger.SCHEDULE.value == "schedule"
        assert JobTrigger.PIPELINE.value == "pipeline"


def test_cancel_transitions_through_cancelling_to_cancelled() -> None:
    """cancel_current() should set CANCELLING, worker then reaches CANCELLED."""
    runtime = JobRuntime(total_steps=100, step_delay=0.02)

    runtime.start_demo()
    snapshot = runtime.cancel_current()
    assert snapshot.status is JobStatus.CANCELLING

    wait_for_status(runtime, JobStatus.CANCELLED)
    events = runtime.current_snapshot().events
    assert any(e.kind is EventKind.JOB_CANCELLING for e in events)
    assert events[-1].kind is EventKind.JOB_CANCELLED