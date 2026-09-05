"""Tests for the in-memory event bus: coalescing, bounded history,
blocking read, timeout, and close scenarios.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Thread
from time import monotonic

from devbase.application.event_bus import InMemoryEventBus
from devbase.domain.events import EventKind, RuntimeEvent


def _event(
    kind: EventKind,
    *,
    job_id: str = "job-1",
    progress: int = 0,
    event_id: str | None = None,
) -> RuntimeEvent:
    return RuntimeEvent(
        sequence=0,
        event_id=event_id or f"{kind.value}-{progress}",
        job_id=job_id,
        kind=kind,
        status=job_id,  # status string; not relevant for bus logic
        progress=progress,
        message=kind.value,
        created_at=datetime.now(timezone.utc),
    )


class TestCoalescing:
    def test_progress_merge_keeps_latest(self) -> None:
        bus = InMemoryEventBus()
        bus.publish(_event(EventKind.PROGRESS, progress=10))
        bus.publish(_event(EventKind.PROGRESS, progress=50))
        bus.publish(_event(EventKind.PROGRESS, progress=90))
        events = bus.snapshot().events
        assert len(events) == 1
        assert events[0].progress == 90

    def test_critical_events_not_coalesced(self) -> None:
        bus = InMemoryEventBus()
        for kind in (
            EventKind.JOB_CREATED,
            EventKind.JOB_STARTED,
            EventKind.PROGRESS,
            EventKind.JOB_SUCCEEDED,
        ):
            bus.publish(_event(kind))
        events = bus.snapshot().events
        assert len(events) == 4
        assert [e.kind for e in events] == [
            EventKind.JOB_CREATED,
            EventKind.JOB_STARTED,
            EventKind.PROGRESS,
            EventKind.JOB_SUCCEEDED,
        ]

    def test_progress_for_different_jobs_not_merged(self) -> None:
        bus = InMemoryEventBus()
        bus.publish(_event(EventKind.PROGRESS, job_id="job-a"))
        bus.publish(_event(EventKind.PROGRESS, job_id="job-b"))
        events = bus.snapshot().events
        assert len(events) == 2


class TestBoundedHistory:
    def test_overflow_drops_oldest(self) -> None:
        bus = InMemoryEventBus(history_size=3)
        for i in range(5):
            bus.publish(_event(EventKind.JOB_CREATED, progress=i))
        events = bus.snapshot().events
        assert len(events) == 3
        # Oldest events evicted; remaining start at progress=2
        assert events[0].progress == 2
        assert events[-1].progress == 4

    def test_cursor_increments_even_on_overflow(self) -> None:
        bus = InMemoryEventBus(history_size=1)
        for i in range(3):
            bus.publish(_event(EventKind.JOB_CREATED, progress=i))
        assert bus.snapshot().cursor == 3


class TestSnapshotWithCursor:
    def test_after_sequence_filters_old_events(self) -> None:
        bus = InMemoryEventBus()
        bus.publish(_event(EventKind.JOB_CREATED, progress=0))
        snap1 = bus.snapshot()
        bus.publish(_event(EventKind.JOB_STARTED, progress=0))
        snap2 = bus.snapshot(after_sequence=snap1.cursor)
        assert len(snap2.events) == 1
        assert snap2.events[0].kind is EventKind.JOB_STARTED


class TestBlockingRead:
    def test_wait_returns_when_event_published(self) -> None:
        bus = InMemoryEventBus()
        results: tuple[RuntimeEvent, ...] = ()

        def waiter():
            nonlocal results
            results = bus.wait_for_events(0, timeout=2.0)

        t = Thread(target=waiter, daemon=True)
        t.start()
        # Give waiter a moment to enter Condition.wait
        import time

        time.sleep(0.05)
        bus.publish(_event(EventKind.JOB_CREATED))
        t.join(timeout=2.0)
        assert not t.is_alive()
        assert len(results) == 1
        assert results[0].kind is EventKind.JOB_CREATED

    def test_wait_timeout_returns_empty(self) -> None:
        bus = InMemoryEventBus()
        start = monotonic()
        result = bus.wait_for_events(0, timeout=0.05)
        elapsed = monotonic() - start
        assert result == ()
        assert elapsed >= 0.04

    def test_wait_returns_existing_events_immediately(self) -> None:
        bus = InMemoryEventBus()
        bus.publish(_event(EventKind.JOB_CREATED))
        bus.publish(_event(EventKind.JOB_STARTED))
        events = bus.wait_for_events(0, timeout=0.01)
        assert len(events) == 2


class TestReconnectRecovery:
    def test_cursor_based_replay_after_disconnect(self) -> None:
        """Simulate WS disconnect and reconnect: events after cursor are
        delivered, progress coalescing preserved."""
        bus = InMemoryEventBus()
        bus.publish(_event(EventKind.JOB_CREATED))
        bus.publish(_event(EventKind.PROGRESS, progress=25))
        snap = bus.snapshot()  # client disconnects here
        cursor = snap.cursor

        # Meanwhile, more events happen
        bus.publish(_event(EventKind.PROGRESS, progress=75))
        bus.publish(_event(EventKind.JOB_SUCCEEDED))

        # Reconnect: get events after cursor
        replay = bus.snapshot(after_sequence=cursor)
        assert [e.kind for e in replay.events] == [
            EventKind.PROGRESS,
            EventKind.JOB_SUCCEEDED,
        ]
        assert replay.events[0].progress == 75
