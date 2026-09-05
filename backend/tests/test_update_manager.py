"""Tests for staged update manager progress and replacement flow."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from devbase.application.update_checker import (
    ReleaseAsset,
    ReleaseInfo,
    ReleaseVersion,
    UpdateCheckResult,
    UpdateConfig,
)
from devbase.desktop.update_manager import UpdateManager


class FakeClient:
    def __init__(self, archive_source: Path):
        self.config = UpdateConfig(asset_prefix="SYNTEC_DevBase-")
        self.archive_source = archive_source

    def check(self, _current):
        asset = ReleaseAsset(
            "SYNTEC_DevBase-1.1.0.zip",
            "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/download/v1.1.0/SYNTEC_DevBase-1.1.0.zip",
            self.archive_source.stat().st_size,
        )
        release = ReleaseInfo(
            "v1.1.0",
            ReleaseVersion(1, 1, 0),
            "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/tag/v1.1.0",
            asset,
        )
        return UpdateCheckResult(
            ReleaseVersion(1, 0, 0),
            ReleaseVersion(1, 1, 0),
            True,
            True,
            release,
        )

    def download_asset(self, _asset, destination):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / "release.zip"
        target.write_bytes(self.archive_source.read_bytes())
        return target


def make_archive(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("SYNTEC_DevBase/SYNTEC_DevBase.exe", b"new")
        archive.writestr(
            "SYNTEC_DevBase/SYNTEC_DevBase-updater.exe",
            b"updater",
        )
    return path


def test_manager_stage_writes_ready_progress(tmp_path: Path) -> None:
    source = make_archive(tmp_path / "source.zip")
    install = tmp_path / "install"
    install.mkdir()
    manager = UpdateManager(
        "1.0.0",
        client=FakeClient(source),
        install_dir=install,
        update_root=tmp_path / "updates",
    )

    ready = manager.stage()

    assert ready.staged_dir.name == "SYNTEC_DevBase"
    assert manager.progress().status == "ready"
    assert manager.progress().ready_file is not None
    assert Path(manager.progress().ready_file).is_file()


def test_manager_apply_updates_progress_and_files(tmp_path: Path) -> None:
    source = make_archive(tmp_path / "source.zip")
    install = tmp_path / "install"
    install.mkdir()
    (install / "SYNTEC_DevBase.exe").write_bytes(b"old")
    manager = UpdateManager(
        "1.0.0",
        client=FakeClient(source),
        install_dir=install,
        update_root=tmp_path / "updates",
    )
    manager.stage()

    progress = manager.apply()

    assert progress.status == "succeeded"
    assert (install / "SYNTEC_DevBase.exe").read_bytes() == b"new"


def test_manager_apply_requires_staged_update(tmp_path: Path) -> None:
    manager = UpdateManager(
        "1.0.0",
        client=FakeClient(make_archive(tmp_path / "source.zip")),
        install_dir=tmp_path / "install",
        update_root=tmp_path / "updates",
    )
    with pytest.raises(RuntimeError, match="staged"):
        manager.apply()
