"""Window lifecycle policy tests."""

from __future__ import annotations

from time import monotonic, sleep

from devbase.api.app import create_app
from devbase.application.job_runtime import JobRuntime
from devbase.application.lifecycle import LifecyclePolicy, WindowCloseMode
from devbase.domain.job import JobStatus


def wait_for_status(runtime: JobRuntime, expected: JobStatus) -> None:
    deadline = monotonic() + 2
    while monotonic() < deadline:
        job = runtime.current_job()
        if job is not None and job.status is expected:
            return
        sleep(0.005)
    raise AssertionError(f"job did not reach {expected}")


def test_stop_on_close_cancels_running_job() -> None:
    runtime = JobRuntime(total_steps=100, step_delay=0.01)
    app = create_app(runtime=runtime)
    app.state.window_lifecycle.policy = type(app.state.window_lifecycle.policy)(
        WindowCloseMode.STOP_ON_CLOSE
    )
    runtime.start_demo()

    result = app.state.window_lifecycle.handle_window_close()

    assert result.mode is WindowCloseMode.STOP_ON_CLOSE
    assert result.stop_requested is True
    wait_for_status(runtime, JobStatus.CANCELLED)


def test_continue_on_close_leaves_running_job_active() -> None:
    runtime = JobRuntime(total_steps=100, step_delay=0.01)
    app = create_app(runtime=runtime)
    runtime.start_demo()

    result = app.state.window_lifecycle.handle_window_close()

    assert result.mode is WindowCloseMode.CONTINUE_ON_CLOSE
    assert result.stop_requested is False
    assert runtime.current_job().status.is_active
    runtime.cancel_current()
    wait_for_status(runtime, JobStatus.CANCELLED)


def test_close_of_terminal_job_does_not_request_stop() -> None:
    runtime = JobRuntime(total_steps=1, step_delay=0)
    app = create_app(
        runtime=runtime,
        lifecycle_policy=LifecyclePolicy(WindowCloseMode.STOP_ON_CLOSE),
    )
    runtime.start_demo()
    wait_for_status(runtime, JobStatus.SUCCEEDED)

    result = app.state.window_lifecycle.handle_window_close()

    assert result.mode is WindowCloseMode.STOP_ON_CLOSE
    assert result.stop_requested is False
    assert runtime.current_job().status is JobStatus.SUCCEEDED