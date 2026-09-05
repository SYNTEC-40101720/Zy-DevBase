"""Tests for safe extraction, ready protocol, and staged rollback."""

from __future__ import annotations

import json
import stat
import zipfile
from pathlib import Path

import pytest

from devbase.desktop.update_helper import (
    ReadyUpdate,
    UpdateApplyError,
    apply_staged_update,
    read_ready_file,
    require_release_files,
    safe_extract_zip,
    write_ready_file,
)


def make_zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return path


def test_safe_extract_requires_one_top_level_directory(tmp_path: Path) -> None:
    archive = make_zip(
        tmp_path / "release.zip",
        {
            "SYNTEC_DevBase/SYNTEC_DevBase.exe": b"exe",
            "other/readme.txt": b"bad",
        },
    )
    with pytest.raises(UpdateApplyError, match="one top-level"):
        safe_extract_zip(archive, tmp_path / "out")


def test_safe_extract_rejects_path_traversal(tmp_path: Path) -> None:
    archive = make_zip(
        tmp_path / "release.zip",
        {"SYNTEC_DevBase/../outside.txt": b"bad"},
    )
    with pytest.raises(UpdateApplyError, match="unsafe"):
        safe_extract_zip(archive, tmp_path / "out")


def test_safe_extract_rejects_absolute_path(tmp_path: Path) -> None:
    archive = make_zip(tmp_path / "release.zip", {"/absolute.txt": b"bad"})
    with pytest.raises(UpdateApplyError, match="absolute"):
        safe_extract_zip(archive, tmp_path / "out")


def test_safe_extract_rejects_symlink(tmp_path: Path) -> None:
    archive_path = tmp_path / "release.zip"
    info = zipfile.ZipInfo("SYNTEC_DevBase/link")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(info, "target")

    with pytest.raises(UpdateApplyError, match="symbolic"):
        safe_extract_zip(archive_path, tmp_path / "out")


def test_safe_extract_and_validate_files(tmp_path: Path) -> None:
    archive = make_zip(
        tmp_path / "release.zip",
        {
            "SYNTEC_DevBase/SYNTEC_DevBase.exe": b"exe",
            "SYNTEC_DevBase/_internal/base_library.zip": b"lib",
        },
    )
    root = safe_extract_zip(
        archive,
        tmp_path / "out",
        expected_top_level="SYNTEC_DevBase",
    )
    require_release_files(root, executable_name="SYNTEC_DevBase.exe")
    assert (root / "SYNTEC_DevBase.exe").read_bytes() == b"exe"


def test_ready_file_round_trip(tmp_path: Path) -> None:
    ready = ReadyUpdate(
        staged_dir=tmp_path / "staged",
        install_dir=tmp_path / "install",
        backup_dir=tmp_path / "backup",
        process_id=123,
    )
    path = write_ready_file(tmp_path / "ready.json", ready)
    loaded = read_ready_file(path)
    assert loaded == ready
    assert json.loads(path.read_text(encoding="utf-8"))["process_id"] == 123


def test_apply_preserves_user_data_and_cleans_backup(tmp_path: Path) -> None:
    install = tmp_path / "install"
    staged = tmp_path / "staged"
    backup = tmp_path / "backup"
    install.mkdir()
    staged.mkdir()
    (install / "SYNTEC_DevBase.exe").write_bytes(b"old")
    (install / "config").mkdir()
    (install / "config" / "settings.ini").write_bytes(b"user")
    (staged / "SYNTEC_DevBase.exe").write_bytes(b"new")
    restarted: list[Path] = []

    apply_staged_update(
        staged,
        install,
        backup,
        preserved_paths=("config",),
        restart=restarted.append,
    )

    assert (install / "SYNTEC_DevBase.exe").read_bytes() == b"new"
    assert (install / "config" / "settings.ini").read_bytes() == b"user"
    assert not backup.exists()
    assert restarted == [install]


def test_apply_rolls_back_when_restart_fails(tmp_path: Path) -> None:
    install = tmp_path / "install"
    staged = tmp_path / "staged"
    backup = tmp_path / "backup"
    install.mkdir()
    staged.mkdir()
    (install / "SYNTEC_DevBase.exe").write_bytes(b"old")
    (staged / "SYNTEC_DevBase.exe").write_bytes(b"new")

    with pytest.raises(UpdateApplyError, match="rolled back"):
        apply_staged_update(
            staged,
            install,
            backup,
            restart=lambda _path: (_ for _ in ()).throw(RuntimeError("boom")),
        )

    assert (install / "SYNTEC_DevBase.exe").read_bytes() == b"old"
    assert not backup.exists()
    assert (tmp_path / "install.failed").exists()


def test_apply_refuses_failed_process_wait(tmp_path: Path) -> None:
    install = tmp_path / "install"
    staged = tmp_path / "staged"
    install.mkdir()
    staged.mkdir()
    with pytest.raises(UpdateApplyError, match="did not exit"):
        apply_staged_update(
            staged,
            install,
            tmp_path / "backup",
            process_id=123,
            wait_for_exit=lambda _pid: False,
        )
