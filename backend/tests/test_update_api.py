"""Tests for the token-protected, notification-only update endpoint."""

from __future__ import annotations

import io
import json
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from devbase import __version__
from devbase.api.app import create_app
from devbase.application.update_checker import GitHubReleaseClient

TOKEN = "test-token"
RELEASE_URL = "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/tag/v99.0.0"


def make_client(*, offline=False):
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        if offline:
            raise TimeoutError("offline")
        return io.BytesIO(json.dumps({
            "tag_name": "v99.0.0", "html_url": RELEASE_URL,
            "draft": False, "prerelease": False,
        }).encode("utf-8"))

    app = create_app(
        local_token=TOKEN,
        update_client=GitHubReleaseClient(opener=opener),
    )
    return TestClient(app), calls


def test_application_start_and_health_do_not_check_github() -> None:
    client, calls = make_client()
    assert client.get("/api/v1/health", headers={"X-Local-Token": TOKEN}).status_code == 200
    assert calls == []
    assert not hasattr(cast(FastAPI, client.app).state, "update_manager")


def test_check_requires_local_token() -> None:
    client, calls = make_client()
    for headers in ({}, {"X-Local-Token": "wrong"}):
        assert client.get("/api/v1/updates/check", headers=headers).status_code == 401
    assert calls == []


def test_check_returns_version_and_manual_release_link_only() -> None:
    client, calls = make_client()
    response = client.get("/api/v1/updates/check", headers={"X-Local-Token": TOKEN})
    assert response.status_code == 200
    assert response.json() == {
        "current": __version__, "latest": "99.0.0", "available": True,
        "release_url": RELEASE_URL, "error": None,
    }
    assert len(calls) == 1


def test_check_failure_does_not_break_local_tools() -> None:
    client, _ = make_client(offline=True)
    response = client.get("/api/v1/updates/check", headers={"X-Local-Token": TOKEN})
    assert response.status_code == 200
    assert response.json()["error"] == "offline"
    assert response.json()["latest"] is None
    assert client.get("/api/v1/health", headers={"X-Local-Token": TOKEN}).status_code == 200
    assert client.get("/api/v1/tools", headers={"X-Local-Token": TOKEN}).status_code == 200


@pytest.mark.parametrize("method,path", [
    ("POST", "/apply"), ("POST", "/apply-and-restart"), ("GET", "/progress"),
])
def test_installation_endpoints_are_removed(method, path) -> None:
    client, calls = make_client()
    response = client.request(method, "/api/v1/updates" + path, headers={"X-Local-Token": TOKEN})
    assert response.status_code == 404
    assert calls == []


def test_openapi_contains_no_update_write_operations() -> None:
    client, _ = make_client()
    paths = cast(FastAPI, client.app).openapi()["paths"]
    assert [path for path in paths if "/updates/" in path] == ["/api/v1/updates/check"]
    assert set(paths["/api/v1/updates/check"]) == {"get"}
