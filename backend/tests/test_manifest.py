"""Tests for the declarative tool manifest, ports, and resource provider.

These cover the NavCategory-style ``ToolRegistry``/``ToolDescriptor``
and the ``AppResourceProvider``-style ``ResourceProvider``.
"""

from __future__ import annotations

import threading

from platform_runtime.application.manifest import ToolDescriptor, ToolRegistry
from platform_runtime.application.task import TaskContext, TaskNotFoundError
from platform_runtime.domain.ports import ProgressSink
from platform_runtime.domain.resources import InMemoryResourceProvider, get_default


def _ctx() -> TaskContext:
    return TaskContext(
        job_id="job-1",
        kind="demo",
        cancel_event=threading.Event(),
        report=lambda _p, _m: None,
    )


def test_tool_registry_round_trip_and_metadata() -> None:
    registry = ToolRegistry()
    descriptor = ToolDescriptor(
        kind="calculator",
        title="计算器",
        group="tool",
        glyph="calc",
        access_key="c",
        supports_input=False,
        task=lambda _ctx: {"done": True},
    )
    registry.register(descriptor)

    assert registry.has("calculator")
    assert registry.get("calculator") is descriptor
    assert registry.kinds() == ["calculator"]
    assert registry.descriptors() == [descriptor]
    assert registry.groups() == ["tool"]


def test_tool_registry_unknown_kind_raises_not_found() -> None:
    registry = ToolRegistry()
    try:
        registry.get("nope")
    except TaskNotFoundError as exc:
        assert exc.kind == "nope"
    else:
        raise AssertionError("expected TaskNotFoundError")


def test_tool_registry_sorts_descriptors_by_group_then_kind() -> None:
    registry = ToolRegistry()
    for kind, group in [("zeta", "b"), ("alpha", "b"), ("mid", "a")]:
        registry.register(
            ToolDescriptor(
                kind=kind,
                title=kind,
                group=group,
                glyph="x",
                task=lambda _ctx: {"done": True},
            )
        )
    ordered = [d.kind for d in registry.descriptors()]
    assert ordered == ["mid", "alpha", "zeta"]


def test_task_context_satisfies_progress_sink_protocol() -> None:
    ctx = _ctx()
    assert isinstance(ctx, ProgressSink)
    assert ctx.is_cancelled() is False
    ctx.report_progress(0.5, "half")
    # report is a no-op stub here; just must not raise


def test_resource_provider_resolves_and_formats() -> None:
    provider = InMemoryResourceProvider()
    assert provider.string("job.queued", kind="demo") == "任务已排队: demo"
    assert provider.string("demo.progress", step=3, total=10) == "演示任务进度 3/10"
    # unknown key falls back to the key itself, never raises
    assert provider.string("no.such.key") == "no.such.key"
    # missing format arg returns the template verbatim
    assert provider.string("job.queued") == "任务已排队: {kind}"


def test_default_provider_is_a_singleton_returning_chinese() -> None:
    first = get_default()
    second = get_default()
    assert first is second
    assert first.string("job.completed") == "任务已完成"


def test_resource_provider_can_be_overridden_per_instance() -> None:
    provider = InMemoryResourceProvider({"job.completed": "done"})
    assert provider.string("job.completed") == "done"
    # built-in keys still present unless overridden
    assert provider.string("job.cancelled") == "任务已取消"
