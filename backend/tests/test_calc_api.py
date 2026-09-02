"""Integration tests for the calculator HTTP API.

Exercises the full stack: ``CalculatorSession`` -> ``CalculatorEngine``
-> ``CalculatorDisplay``, wired through the FastAPI app and the
``/api/v1/calc`` router. Verifies state retrieval, key press flow,
history accumulation, and error handling for unknown keys.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from platform_runtime.api.app import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_calc_initial_state() -> None:
    client = _client()
    response = client.get("/api/v1/calc/state")
    assert response.status_code == 200
    body = response.json()
    assert body["display"] == "0"
    assert body["error"] is False
    assert body["expression"] == []
    assert body["memory"] == []
    assert body["history"] == []


def test_calc_press_digit_then_add() -> None:
    client = _client()
    # 2 + 3 =
    for key in ("2", "+", "3", "="):
        r = client.post("/api/v1/calc/press", json={"key": key})
        assert r.status_code == 200
    body = client.get("/api/v1/calc/state").json()
    assert body["display"] == "5"
    assert body["history"] == [{"expression": "2 + 3", "result": "5"}]


def test_calc_chained_operators() -> None:
    client = _client()
    # 2 + 3 * 4 =  -> (2+3)=5, 5*4=20
    for key in ("2", "+", "3", "*", "4", "="):
        client.post("/api/v1/calc/press", json={"key": key})
    assert client.get("/api/v1/calc/state").json()["display"] == "20"


def test_calc_division_by_zero_freezes() -> None:
    client = _client()
    for key in ("5", "/", "0", "="):
        client.post("/api/v1/calc/press", json={"key": key})
    body = client.get("/api/v1/calc/state").json()
    assert body["error"] is True
    # frozen — further digits ignored
    client.post("/api/v1/calc/press", json={"key": "7"})
    assert client.get("/api/v1/calc/state").json()["error"] is True
    # clear unfreezes
    client.post("/api/v1/calc/press", json={"key": "C"})
    body = client.get("/api/v1/calc/state").json()
    assert body["error"] is False
    assert body["display"] == "0"


def test_calc_memory_store_and_recall() -> None:
    client = _client()
    for key in ("5", "MS"):
        client.post("/api/v1/calc/press", json={"key": key})
    body = client.get("/api/v1/calc/state").json()
    assert body["memory"] == ["5"]
    # clear, then recall
    client.post("/api/v1/calc/press", json={"key": "C"})
    client.post("/api/v1/calc/press", json={"key": "MR"})
    assert client.get("/api/v1/calc/state").json()["display"] == "5"


def test_calc_unknown_key_returns_400() -> None:
    client = _client()
    response = client.post("/api/v1/calc/press", json={"key": "BOGUS"})
    assert response.status_code == 400


def test_calc_state_is_independent_of_jobs() -> None:
    """Calculator session lives alongside the job runtime without interference."""
    client = _client()
    client.post("/api/v1/calc/press", json={"key": "9"})
    # health still works (runtime untouched)
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["active_job_id"] is None
    # calculator state preserved
    assert client.get("/api/v1/calc/state").json()["display"] == "9"
