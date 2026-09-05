"""Tests for the generic INI configuration manager."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

from devbase.config_manager import ConfigManager


def test_first_use_creates_app_template(tmp_path: Path) -> None:
    path = tmp_path / "settings.ini"

    config = ConfigManager(path)

    assert path.is_file()
    assert config.sections() == ["app"]
    assert config.get("app", "name") == "DevBase"
    assert config.get("app", "config_version") == "1"


def test_set_and_read_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.ini"
    config = ConfigManager(path)

    config.set("app", "display_name", "Test Tool")
    config.set("runtime", "port", 8123)

    reloaded = ConfigManager(path)
    assert reloaded.get("app", "display_name") == "Test Tool"
    assert reloaded.get("runtime", "port") == "8123"


def test_missing_value_uses_fallback(tmp_path: Path) -> None:
    config = ConfigManager(tmp_path / "settings.ini")

    assert config.get("app", "missing", fallback="fallback") == "fallback"
    assert config.get("missing", "value") is None


def test_reload_config_picks_up_external_change(tmp_path: Path) -> None:
    path = tmp_path / "settings.ini"
    config = ConfigManager(path)
    external = ConfigParser(interpolation=None)
    external.read(path, encoding="utf-8")
    external.set("app", "name", "Changed")
    with path.open("w", encoding="utf-8", newline="") as stream:
        external.write(stream)

    config.reload_config()

    assert config.get("app", "name") == "Changed"


def test_set_preserves_values_written_by_another_manager(tmp_path: Path) -> None:
    path = tmp_path / "settings.ini"
    first = ConfigManager(path)
    second = ConfigManager(path)

    first.set("tool", "one", "1")
    second.set("tool", "two", "2")

    final = ConfigManager(path)
    assert final.get("tool", "one") == "1"
    assert final.get("tool", "two") == "2"


def test_custom_defaults_are_supported_without_business_sections(
    tmp_path: Path,
) -> None:
    config = ConfigManager(
        tmp_path / "settings.ini",
        defaults={"app": {"name": "Custom", "mode": "test"}},
    )

    assert config.sections() == ["app"]
    assert config.as_dict()["app"] == {"name": "Custom", "mode": "test"}


def test_reload_is_chainable(tmp_path: Path) -> None:
    config = ConfigManager(tmp_path / "settings.ini")
    assert config.reload_config() is config


def test_lock_file_is_created(tmp_path: Path) -> None:
    path = tmp_path / "settings.ini"
    ConfigManager(path)
    assert (tmp_path / "settings.ini.lock").is_file()
