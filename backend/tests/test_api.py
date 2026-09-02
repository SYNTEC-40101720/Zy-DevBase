from pathlib import Path
from time import monotonic, sleep

from fastapi.testclient import TestClient

from zy_devbase.api.app import create_app
from zy_devbase.application.job_runtime import JobRuntime
from zy_devbase.application.lifecycle import LifecyclePolicy, WindowCloseMode
from zy_devbase.domain.job import JobStatus


def wait_for_terminal(runtime: JobRuntime) -> None:
    deadline = monotonic() + 2
    while monotonic() < deadline:
        job = runtime.current_job()
        if job is not None and job.status.is_terminal:
            return
        sleep(0.005)
    raise AssertionError("job did not become terminal")


def test_static_frontend_does_not_mask_api(tmp_path: Path) -> None:
    index_path = tmp_path / "index.html"
    index_path.write_text("<html>template</html>", encoding="utf-8")
    client = TestClient(create_app(static_dir=tmp_path))

    assert client.get("/").status_code == 200
    assert client.get("/").text == "<html>template</html>"
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health").json()["service"] == "zy"


def test_health_reports_window_close_mode() -> None:
    client = TestClient(
        create_app(
            lifecycle_policy=LifecyclePolicy(WindowCloseMode.STOP_ON_CLOSE),
        )
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["window_close_mode"] == "stop_on_close"


def test_api_start_conflict_and_cancel() -> None:
    runtime = JobRuntime(total_steps=100, step_delay=0.02)
    client = TestClient(create_app(runtime))

    started = client.post("/api/v1/jobs/start")
    assert started.status_code == 201
    assert started.json()["status"] == "queued"
    assert client.post("/api/v1/jobs/start").status_code == 409

    cancelled = client.post("/api/v1/jobs/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_websocket_initial_snapshot_and_reconnect_recovery() -> None:
    runtime = JobRuntime(total_steps=3, step_delay=0.005)
    client = TestClient(create_app(runtime))

    with client.websocket_connect("/api/v1/events") as websocket:
        health = websocket.receive_json()
        assert health["type"] == "health"
        assert health["data"]["window_close_mode"] == "continue_on_close"
        initial = websocket.receive_json()
        assert initial["type"] == "snapshot"
        assert initial["data"]["job"] is None

        started = client.post("/api/v1/jobs/start")
        assert started.status_code == 201
        event = websocket.receive_json()
        assert event["type"] == "event"
        assert event["data"]["kind"] == "job_created"

    wait_for_terminal(runtime)

    with client.websocket_connect("/api/v1/events") as websocket:
        assert websocket.receive_json()["type"] == "health"
        recovered = websocket.receive_json()
        assert recovered["type"] == "snapshot"
        assert recovered["data"]["job"]["status"] == JobStatus.COMPLETED.value
        assert any(
            event["kind"] == "job_completed"
            for event in recovered["data"]["events"]
        )


def test_tools_endpoint_returns_registered_descriptors() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    tools = response.json()["tools"]
    assert isinstance(tools, list)
    assert len(tools) >= 1
    demo = next(t for t in tools if t["kind"] == "demo_long_task")
    assert demo["title"]
    assert demo["mode"] == "oneshot"