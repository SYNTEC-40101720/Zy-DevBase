"""Tests for the generic native bridge."""

from __future__ import annotations

from pathlib import Path

from devbase.desktop.native_bridge import NativeBridge


def test_select_directory_uses_injected_picker() -> None:
    calls: list[str] = []
    bridge = NativeBridge(
        directory_picker=lambda title: calls.append(title) or "C:/picked"
    )

    assert bridge.select_directory() == "C:/picked"
    assert calls == ["选择文件夹"]


def test_select_directory_can_return_none() -> None:
    bridge = NativeBridge(directory_picker=lambda _title: None)
    assert bridge.select_directory("Choose") is None


def test_open_directory_rejects_missing_path(tmp_path: Path) -> None:
    opened: list[Path] = []
    bridge = NativeBridge(directory_opener=opened.append)

    assert bridge.open_directory(str(tmp_path / "missing")) is False
    assert opened == []


def test_open_directory_applies_checker(tmp_path: Path) -> None:
    opened: list[Path] = []
    bridge = NativeBridge(directory_opener=opened.append)

    assert bridge.open_directory(str(tmp_path), checker=lambda _path: False) is False
    assert opened == []


def test_open_directory_uses_injected_opener(tmp_path: Path) -> None:
    opened: list[Path] = []
    bridge = NativeBridge(directory_opener=opened.append)

    assert bridge.open_directory(str(tmp_path)) is True
    assert opened == [tmp_path]


def test_runtime_info_is_json_serializable() -> None:
    bridge = NativeBridge(platform_name="test-platform")

    info = bridge.get_runtime_info()

    assert info["platform"] == "test-platform"
    assert info["app_version"]
    assert info["python_version"]
    assert info["executable"]
    assert isinstance(info["frozen"], bool)
    assert isinstance(info["app_dir"], str)


def test_windows_and_non_windows_substitutes_are_supported(tmp_path: Path) -> None:
    opened: list[Path] = []
    windows = NativeBridge(
        directory_picker=lambda _title: "C:/windows",
        directory_opener=opened.append,
        platform_name="win32",
    )
    non_windows = NativeBridge(
        directory_picker=lambda _title: "/tmp/non-windows",
        directory_opener=opened.append,
        platform_name="linux",
    )

    assert windows.select_directory() == "C:/windows"
    assert non_windows.select_directory() == "/tmp/non-windows"
    assert windows.open_directory(str(tmp_path)) is True
    assert non_windows.open_directory(str(tmp_path)) is True
    assert opened == [tmp_path, tmp_path]
