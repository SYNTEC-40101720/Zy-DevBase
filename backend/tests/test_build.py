"""Tests for the version synchronization tool."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("bump_version", _ROOT / "bump_version.py")
assert _SPEC is not None and _SPEC.loader is not None
bump_version = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = bump_version
_SPEC.loader.exec_module(bump_version)


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


precheck = _load_script("precheck", _ROOT / "scripts" / "precheck.py")
build_release = _load_script(
    "build_release",
    _ROOT / "scripts" / "build_release.py",
)


def test_semver_bump_parts() -> None:
    current = bump_version.Version.parse("1.2.3")
    assert str(bump_version.bump(current, "patch")) == "1.2.4"
    assert str(bump_version.bump(current, "minor")) == "1.3.0"
    assert str(bump_version.bump(current, "major")) == "2.0.0"


def test_windows_tuple() -> None:
    assert bump_version.Version.parse("1.2.3").windows_tuple() == "(1, 2, 3, 0)"
    assert bump_version.Version.parse("1.2.3").windows_string() == "1.2.3.0"


def test_invalid_semver_rejected() -> None:
    with pytest.raises(bump_version.VersionSyncError):
        bump_version.Version.parse("1.2")


def test_current_repository_is_consistent() -> None:
    problems = bump_version.check_consistency(_ROOT)
    assert problems == []


def test_packaging_precheck_passes() -> None:
    assert precheck.run_precheck(_ROOT) == []


def test_zip_bundle_writes_archive_and_checksum(tmp_path: Path) -> None:
    bundle = tmp_path / "SYNTEC_DevBase"
    internal = bundle / "_internal"
    internal.mkdir(parents=True)
    (internal / "SYNTEC_DevBase.exe").write_bytes(b"exe")
    (internal / "base_library.zip").write_bytes(b"library")

    archive, checksum = build_release.zip_bundle(bundle, tmp_path / "release", "1.2.3")

    assert archive.is_file()
    assert checksum.is_file()
    assert archive.name == "SYNTEC_DevBase-1.2.3.zip"
    assert "SYNTEC_DevBase/_internal/SYNTEC_DevBase.exe" in ZipFile(archive).namelist()
    assert archive.name in checksum.read_text(encoding="ascii")


def test_check_is_read_only() -> None:
    before = {
        path: path.read_bytes()
        for path in (
            _ROOT / "version.py",
            _ROOT / "backend" / "pyproject.toml",
            _ROOT / "web" / "package.json",
            _ROOT / "web" / "package-lock.json",
            _ROOT / "version_info.txt",
        )
    }
    result = subprocess.run(
        [sys.executable, str(_ROOT / "bump_version.py"), "--check"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "consistency OK" in result.stdout
    for path, content in before.items():
        assert path.read_bytes() == content
