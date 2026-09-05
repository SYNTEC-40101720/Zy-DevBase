"""Tests for token-protected update endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from devbase.api.app import create_app
from devbase.application.update_checker import (
    ReleaseAsset,
    ReleaseInfo,
    ReleaseVersion,
    UpdateCheckResult,
)
from devbase.desktop.update_helper import ReadyUpdate
from devbase.desktop.update_manager import UpdateProgress

TOKEN = "test-token"


class FakeUpdateManager:
    def __init__(self) -> None:
        self.staged = False
        self._progress = UpdateProgress()

    def check(self) -> UpdateCheckResult:
        release = ReleaseInfo(
            "v1.1.0",
            ReleaseVersion(1, 1, 0),
            "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/tag/v1.1.0",
            ReleaseAsset(
                "SYNTEC_DevBase-1.1.0.zip",
                "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/download/v1.1.0/SYNTEC_DevBase-1.1.0.zip",
                10,
            ),
        )
        return UpdateCheckResult(
            ReleaseVersion(1, 0, 0),
            ReleaseVersion(1, 1, 0),
            True,
            True,
            release,
        )

    def stage(self) -> ReadyUpdate:
        self.staged = True
        self._progress = UpdateProgress(
            status="ready",
            percent=80,
            message="update is ready to apply",
            ready_file="C:/temp/ready.json",
        )
        return ReadyUpdate(Path("C:/staged"), Path("C:/install"), Path("C:/backup"))

    def progress(self) -> UpdateProgress:
        return self._progress


def headers() -> dict[str, str]:
    return {"X-Local-Token": TOKEN}


def test_update_check_requires_local_token() -> None:
    client = TestClient(create_app(local_token=TOKEN, update_manager=FakeUpdateManager()))
    assert client.get("/api/v1/updates/check").status_code == 401


def test_update_check_and_progress_use_manager() -> None:
    manager = FakeUpdateManager()
    client = TestClient(create_app(local_token=TOKEN, update_manager=manager))

    checked = client.get("/api/v1/updates/check", headers=headers())
    assert checked.status_code == 200
    assert checked.json()["available"] is True
    assert checked.json()["asset_name"] == "SYNTEC_DevBase-1.1.0.zip"

    before = client.get("/api/v1/updates/progress", headers=headers())
    assert before.json()["status"] == "idle"

    applied = client.post("/api/v1/updates/apply", headers=headers())
    assert applied.status_code == 200
    assert applied.json()["status"] == "ready"
    assert manager.staged is True

    after = client.get("/api/v1/updates/progress", headers=headers())
    assert after.json()["ready_file"] == "C:/temp/ready.json"
