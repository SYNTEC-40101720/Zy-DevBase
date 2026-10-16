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


def test_select_file_uses_injected_picker() -> None:
    picked: list[tuple[str, tuple[tuple[str, str], ...]]] = []

    def picker(title: str, patterns: tuple[tuple[str, str], ...]) -> str | None:
        picked.append((title, patterns))
        return "C:/data/sample.csv"

    bridge = NativeBridge(file_picker=picker)
    result = bridge.select_file("选择文件", (("CSV files", "*.csv"),))

    assert result == "C:/data/sample.csv"
    assert picked == [("选择文件", (("CSV files", "*.csv"),))]


def test_select_file_can_return_none() -> None:
    bridge = NativeBridge(file_picker=lambda _title, _patterns: None)
    assert bridge.select_file() is None


def test_save_file_uses_injected_picker() -> None:
    calls: list[tuple[str, str]] = []

    def saver(title: str, default_name: str) -> str | None:
        calls.append((title, default_name))
        return "C:/data/out.csv"

    bridge = NativeBridge(save_picker=saver)
    result = bridge.save_file("另存为", "out.csv")

    assert result == "C:/data/out.csv"
    assert calls == [("另存为", "out.csv")]


def test_save_file_can_return_none() -> None:
    bridge = NativeBridge(save_picker=lambda _title, _name: None)
    assert bridge.save_file() is None
