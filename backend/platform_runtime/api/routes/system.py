from fastapi import APIRouter, Depends, Request

from platform_runtime.api.dependencies import get_runtime
from platform_runtime.api.schemas import HealthResponse
from platform_runtime.application.job_runtime import JobRuntime

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(
    request: Request,
    runtime: JobRuntime = Depends(get_runtime),
) -> HealthResponse:
    job = runtime.current_job()
    return HealthResponse(
        service="zy",
        active_job_id=None if job is None else job.job_id,
        window_close_mode=request.app.state.window_lifecycle.policy.close_mode,
    )