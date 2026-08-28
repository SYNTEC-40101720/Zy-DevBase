import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from platform_runtime.application.errors import (
    JobAlreadyRunningError,
    JobNotCancellableError,
    NoCurrentJobError,
)
from platform_runtime.application.job_runtime import JobRuntime
from platform_runtime.application.lifecycle import LifecyclePolicy, WindowLifecycle

from .routes import events, jobs, system


def create_app(
    runtime: JobRuntime | None = None,
    static_dir: str | Path | None = None,
    lifecycle_policy: LifecyclePolicy | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Platform Runtime Template",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.state.runtime = runtime or JobRuntime()
    app.state.window_lifecycle = WindowLifecycle(
        lifecycle_policy or LifecyclePolicy(),
        stop_active_job=_stop_active_job(app.state.runtime),
    )
    app.include_router(system.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")

    if static_dir is not None:
        static_path = Path(static_dir)
        if static_path.is_dir() and (static_path / "index.html").is_file():
            app.mount(
                "/",
                StaticFiles(directory=static_path, html=True),
                name="frontend",
            )

    @app.exception_handler(JobAlreadyRunningError)
    async def handle_job_conflict(
        _request: Request,
        _exception: JobAlreadyRunningError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "a non-terminal job is already running"},
        )

    @app.exception_handler(NoCurrentJobError)
    async def handle_missing_job(
        _request: Request,
        _exception: NoCurrentJobError,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "no current job"})

    @app.exception_handler(JobNotCancellableError)
    async def handle_terminal_job(
        _request: Request,
        _exception: JobNotCancellableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "the current job is already terminal"},
        )

    return app


def create_app_from_environment() -> FastAPI:
    return create_app(static_dir=os.getenv("PLATFORM_STATIC_DIR"))


def _stop_active_job(runtime: JobRuntime):
    def stop() -> bool:
        try:
            runtime.cancel_current()
        except (NoCurrentJobError, JobNotCancellableError):
            return False
        return True

    return stop


app = create_app()