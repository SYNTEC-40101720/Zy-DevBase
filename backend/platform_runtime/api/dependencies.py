from fastapi import Request

from platform_runtime.application.job_runtime import JobRuntime


def get_runtime(request: Request) -> JobRuntime:
    return request.app.state.runtime