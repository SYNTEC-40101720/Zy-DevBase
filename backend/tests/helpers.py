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


def wait_for_kind(runtime: JobRuntime, expected: str) -> None:
    """等待 current_job 切换到指定 kind 的任务（pipeline 链式启动的竞态防护：
    前一任务 SUCCEEDED 与下一任务 start() 之间存在锁外窗口，仅看状态会把
    两次等待都消耗在同一个任务上）。"""
    deadline = monotonic() + 2
    while monotonic() < deadline:
        job = runtime.current_job()
        if job is not None and job.kind == expected and job.status.is_terminal:
            return
        sleep(0.005)
    raise AssertionError(f"current_job did not become {expected}")
