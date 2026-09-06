from __future__ import annotations

from time import monotonic, sleep

from devbase.application.job_runtime import JobRuntime
from devbase.domain.job import JobStatus


def wait_for_terminal(runtime: JobRuntime) -> None:
    deadline = monotonic() + 2
    while monotonic() < deadline:
        job = runtime.current_job()
        if job is not None and job.status.is_terminal:
            return
        sleep(0.005)
    raise AssertionError("job did not become terminal")


def wait_for_status(runtime: JobRuntime, expected: JobStatus) -> None:
    deadline = monotonic() + 2
    while monotonic() < deadline:
        job = runtime.current_job()
        if job is not None and job.status is expected:
            return
        sleep(0.005)
    raise AssertionError(f"job did not reach {expected}")
