"""Tests for token-protected update endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from devbase.api.app import create_app
from devbase.api.routes import updates
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
        self.install_dir = Path("C:/install")
        self.updater_path = self.install_dir / "SYNTEC_DevBase-updater.exe"
        self.stamped_pid = None
        self.discarded = False

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

    def discard_staged_update(self) -> None:
        self.discarded = True

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

    def prepare_external_apply(self, process_id: int) -> tuple[Path, Path]:
        self.stamped_pid = process_id
        return self.updater_path, Path(self._progress.ready_file)


def headers() -> dict[str, str]:
    return {"X-Local-Token": TOKEN}


def test_apply_and_restart_spawns_updater_and_requests_shutdown(monkeypatch) -> None:
    manager = FakeUpdateManager()
    client = TestClient(create_app(local_token=TOKEN, update_manager=manager))
    shutdown_calls: list[bool] = []
    client.app.state.request_shutdown = lambda: shutdown_calls.append(True)
    spawned: dict[str, object] = {}

    def fake_popen(command, **kwargs):
        spawned["command"] = command
        spawned["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(updates.subprocess, "Popen", fake_popen)

    response = client.post("/api/v1/updates/apply-and-restart", headers=headers())

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert manager.staged is True
    assert manager.stamped_pid is not None
    assert spawned["command"] == [
        str(manager.updater_path),
        "--ready-file",
        str(Path("C:/temp/ready.json")),
    ]
    assert spawned["kwargs"] == {
        "cwd": str(manager.updater_path.parent),
        "close_fds": True,
        "stdin": updates.subprocess.DEVNULL,
        "stdout": updates.subprocess.DEVNULL,
        "stderr": updates.subprocess.DEVNULL,
        "creationflags": (
            updates.subprocess.DETACHED_PROCESS
            if updates.sys.platform == "win32"
            else 0
        ),
    }
    assert shutdown_calls == [True]


def test_apply_and_restart_rejects_non_desktop_mode() -> None:
    manager = FakeUpdateManager()
    client = TestClient(create_app(local_token=TOKEN, update_manager=manager))

    response = client.post("/api/v1/updates/apply-and-restart", headers=headers())

    assert response.status_code == 409
    assert "desktop mode" in response.json()["detail"]
    assert manager.staged is False


def test_apply_and_restart_reports_updater_spawn_failure(monkeypatch) -> None:
    manager = FakeUpdateManager()
    client = TestClient(create_app(local_token=TOKEN, update_manager=manager))
    client.app.state.request_shutdown = lambda: None

    def fail_popen(*_args, **_kwargs):
        raise OSError("cannot spawn updater")

    monkeypatch.setattr(updates.subprocess, "Popen", fail_popen)

    response = client.post("/api/v1/updates/apply-and-restart", headers=headers())

    assert response.status_code == 500
    assert "cannot spawn updater" in response.json()["detail"]
    assert manager.discarded is True


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
