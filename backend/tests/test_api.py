from pathlib import Path
from time import monotonic, sleep

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from devbase.api.app import create_app
from devbase.application.job_runtime import JobRuntime
from devbase.application.lifecycle import LifecyclePolicy, WindowCloseMode
from devbase.domain.job import JobStatus

TEST_TOKEN = "test-token"


def _auth_headers() -> dict[str, str]:
    return {"X-Local-Token": TEST_TOKEN}


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
    client = TestClient(
        create_app(static_dir=tmp_path, local_token=TEST_TOKEN)
    )

    assert client.get("/").status_code == 200
    assert client.get("/").text == "<html>template</html>"
    assert client.get(
        "/api/v1/health",
        headers=_auth_headers(),
    ).status_code == 200
    assert client.get(
        "/api/v1/health",
        headers=_auth_headers(),
    ).json()["service"] == "devbase"


def test_health_reports_window_close_mode() -> None:
    client = TestClient(
        create_app(
            lifecycle_policy=LifecyclePolicy(WindowCloseMode.STOP_ON_CLOSE),
            local_token=TEST_TOKEN,
        )
    )

    response = client.get("/api/v1/health", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["window_close_mode"] == "stop_on_close"


def test_api_start_conflict_and_cancel() -> None:
    runtime = JobRuntime(total_steps=100, step_delay=0.02)
    client = TestClient(create_app(runtime, local_token=TEST_TOKEN))

    started = client.post("/api/v1/jobs/start", headers=_auth_headers())
    assert started.status_code == 201
    assert started.json()["status"] == "queued"
    assert client.post(
        "/api/v1/jobs/start",
        headers=_auth_headers(),
    ).status_code == 409

    cancelled = client.post("/api/v1/jobs/cancel", headers=_auth_headers())
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelling"


def test_websocket_initial_snapshot_and_reconnect_recovery() -> None:
    runtime = JobRuntime(total_steps=3, step_delay=0.005)
    client = TestClient(create_app(runtime, local_token=TEST_TOKEN))

    with client.websocket_connect(
        f"/api/v1/events?token={TEST_TOKEN}"
    ) as websocket:
        health = websocket.receive_json()
        assert health["type"] == "health"
        assert health["data"]["window_close_mode"] == "continue_on_close"
        initial = websocket.receive_json()
        assert initial["type"] == "snapshot"
        assert initial["data"]["job"] is None

        started = client.post("/api/v1/jobs/start", headers=_auth_headers())
        assert started.status_code == 201
        event = websocket.receive_json()
        assert event["type"] == "event"
        assert event["data"]["kind"] == "job_created"

    wait_for_terminal(runtime)

    with client.websocket_connect(
        f"/api/v1/events?token={TEST_TOKEN}"
    ) as websocket:
        assert websocket.receive_json()["type"] == "health"
        recovered = websocket.receive_json()
        assert recovered["type"] == "snapshot"
        assert recovered["data"]["job"]["status"] == JobStatus.SUCCEEDED.value
        assert any(
            event["kind"] == "job_succeeded"
            for event in recovered["data"]["events"]
        )


def test_tools_endpoint_returns_registered_descriptors() -> None:
    client = TestClient(create_app(local_token=TEST_TOKEN))

    response = client.get("/api/v1/tools", headers=_auth_headers())
    assert response.status_code == 200
    tools = response.json()["tools"]
    assert isinstance(tools, list)
    assert len(tools) >= 1
    demo = next(t for t in tools if t["kind"] == "demo_long_task")
    assert demo["title"]
    assert demo["mode"] == "oneshot"


def test_start_unknown_kind_returns_404() -> None:
    client = TestClient(create_app(local_token=TEST_TOKEN))

    response = client.post(
        "/api/v1/jobs/start",
        headers=_auth_headers(),
        json={"kind": "missing-tool"},
    )

    assert response.status_code == 404
    assert "missing-tool" in response.json()["detail"]


def test_api_requires_local_token() -> None:
    client = TestClient(create_app(local_token=TEST_TOKEN))

    assert client.get("/api/v1/health").status_code == 401
    assert client.get(
        "/api/v1/health",
        headers=_auth_headers(),
    ).status_code == 200


# ---------------------------------------------------------------------------
# 任务 1：安全层完整覆盖
# ---------------------------------------------------------------------------

def test_wrong_token_returns_401() -> None:
    """错误 token 应拒绝访问。"""
    client = TestClient(create_app(local_token=TEST_TOKEN))

    bad = client.get(
        "/api/v1/health",
        headers={"X-Local-Token": "wrong-secret"},
    )
    assert bad.status_code == 401

    good = client.get("/api/v1/health", headers=_auth_headers())
    assert good.status_code == 200


def test_correct_token_succeeds_on_all_protected_routes() -> None:
    """正确 token 能访问所有受保护路由。"""
    client = TestClient(create_app(local_token=TEST_TOKEN))

    endpoints = ("/api/v1/health", "/api/v1/jobs/current", "/api/v1/tools")
    for endpoint in endpoints:
        r = client.get(endpoint, headers=_auth_headers())
        assert r.status_code == 200, endpoint


def test_wrong_origin_rejected_when_allowlist_set() -> None:
    """allowed_origins 非空时，浏览器请求带不匹配 Origin 头应 403。"""
    client = TestClient(
        create_app(
            local_token=TEST_TOKEN,
            allowed_origins=["http://localhost:5173"],
        )
    )

    # 匹配的 Origin
    r_ok = client.get(
        "/api/v1/health",
        headers={
            "X-Local-Token": TEST_TOKEN,
            "Origin": "http://localhost:5173",
        },
    )
    assert r_ok.status_code == 200

    # 不匹配的 Origin
    r_bad = client.get(
        "/api/v1/health",
        headers={
            "X-Local-Token": TEST_TOKEN,
            "Origin": "http://evil.example.com",
        },
    )
    assert r_bad.status_code == 403


def test_security_headers_present_on_api_response() -> None:
    """安全响应头应出现在 API 响应中。"""
    client = TestClient(create_app(local_token=TEST_TOKEN))

    r = client.get("/api/v1/health", headers=_auth_headers())
    assert "content-security-policy" in {k.lower() for k in r.headers}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_swagger_disabled_and_openapi_present() -> None:
    """Swagger/ReDoc 不应暴露，但 openapi.json 需保留。"""
    client = TestClient(create_app(local_token=TEST_TOKEN))

    assert client.get("/docs", headers=_auth_headers()).status_code == 404
    assert (
        client.get("/redoc", headers=_auth_headers()).status_code == 404
    )
    spec = client.get(
        "/api/v1/openapi.json",
        headers=_auth_headers(),
    )
    assert spec.status_code == 200
    assert spec.json()["info"]["title"] == "DevBase"


def test_websocket_missing_token_rejected() -> None:
    """WS 不带 token 应 1008 关闭。"""
    client = TestClient(create_app(local_token=TEST_TOKEN))

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/events") as ws:
            ws.receive_json()
    assert exc_info.value.code == 1008


def test_websocket_wrong_token_rejected() -> None:
    """WS 错误 token 应 1008 关闭。"""
    client = TestClient(create_app(local_token=TEST_TOKEN))

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/api/v1/events?token=wrong-secret"
        ) as ws:
            ws.receive_json()
    assert exc_info.value.code == 1008


def test_websocket_correct_token_succeeds() -> None:
    """WS 正确 token 应能连接。"""
    client = TestClient(create_app(local_token=TEST_TOKEN))

    with client.websocket_connect(
        f"/api/v1/events?token={TEST_TOKEN}"
    ) as ws:
        health = ws.receive_json()
    assert health["type"] == "health"


def test_websocket_same_origin_allowed_with_dev_allowlist() -> None:
    """Direct browser hosting on the API port remains same-origin."""
    client = TestClient(
        create_app(
            local_token=TEST_TOKEN,
            allowed_origins=["http://localhost:5173"],
        )
    )

    with client.websocket_connect(
        f"/api/v1/events?token={TEST_TOKEN}",
        headers={"Origin": "http://testserver"},
    ) as websocket:
        assert websocket.receive_json()["type"] == "health"


def test_default_random_token_generated_when_omitted() -> None:
    """未传 local_token 时应自动生成随机 token。独立实例 token 互不相同。"""
    app_a = create_app()
    app_b = create_app()
    assert app_a.state.local_token
    assert app_b.state.local_token
    assert app_a.state.local_token != app_b.state.local_token