from fastapi import APIRouter, Depends

from platform_runtime.api.dependencies import get_runtime
from platform_runtime.api.schemas import JobResponse, SnapshotResponse, snapshot_response
from platform_runtime.application.job_runtime import JobRuntime

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/current", response_model=SnapshotResponse)
def current_job(runtime: JobRuntime = Depends(get_runtime)) -> SnapshotResponse:
    return snapshot_response(runtime.current_snapshot())


@router.post("/start", response_model=JobResponse, status_code=201)
def start_job(runtime: JobRuntime = Depends(get_runtime)) -> JobResponse:
    job = runtime.start_demo()
    return JobResponse(
        id=job.job_id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/cancel", response_model=JobResponse)
def cancel_job(runtime: JobRuntime = Depends(get_runtime)) -> JobResponse:
    job = runtime.cancel_current()
    return JobResponse(
        id=job.job_id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )