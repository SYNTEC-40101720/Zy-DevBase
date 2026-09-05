"""Tests for logger_config: setup, rotation, re-config, frozen mode."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from unittest.mock import patch

import pytest

from devbase.logger_config import setup_logging, _resolve_base_dir, _ensure_logs_dir


@pytest.fixture(autouse=True)
def _clean_logger():
    """Remove all handlers from the 'devbase' logger before and after each test."""
    logger = logging.getLogger("devbase")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    yield
    for handler in list(logger.handlers):
        logger.removeHandler(handler)


def test_setup_logging_creates_logs_dir(tmp_path: Path) -> None:
    log_path = setup_logging(base_dir=tmp_path)
    assert log_path.parent == tmp_path / "logs"
    assert (tmp_path / "logs").is_dir()
    assert log_path.name == "app.log"
    assert log_path.exists()


def test_default_log_name(tmp_path: Path) -> None:
    log_path = setup_logging(base_dir=tmp_path)
    assert log_path.name == "app.log"


def test_custom_log_name(tmp_path: Path) -> None:
    log_path = setup_logging(log_name="custom.log", base_dir=tmp_path)
    assert log_path.name == "custom.log"


def test_repeated_setup_does_not_duplicate_handlers(tmp_path: Path) -> None:
    setup_logging(base_dir=tmp_path)
    count_after_first = len(logging.getLogger("devbase").handlers)
    setup_logging(base_dir=tmp_path)
    count_after_second = len(logging.getLogger("devbase").handlers)
    assert count_after_first == count_after_second


def test_different_log_name_appends_handler(tmp_path: Path) -> None:
    setup_logging(log_name="a.log", base_dir=tmp_path)
    setup_logging(log_name="b.log", base_dir=tmp_path)
    handlers = logging.getLogger("devbase").handlers
    assert len(handlers) == 2


def test_handler_is_rotating_with_1mb_and_5_backups(tmp_path: Path) -> None:
    setup_logging(base_dir=tmp_path)
    handlers = [
        h
        for h in logging.getLogger("devbase").handlers
        if isinstance(h, RotatingFileHandler)
    ]
    assert len(handlers) == 1
    assert handlers[0].maxBytes == 1024 * 1024
    assert handlers[0].backupCount == 5


def test_logging_writes_to_file(tmp_path: Path) -> None:
    setup_logging(base_dir=tmp_path)
    logger = logging.getLogger("devbase")
    logger.info("test message")
    for handler in logger.handlers:
        handler.flush()
    content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "test message" in content
    assert "[INFO]" in content


def test_ensure_logs_dir_idempotent(tmp_path: Path) -> None:
    d1 = _ensure_logs_dir(tmp_path)
    d2 = _ensure_logs_dir(tmp_path)
    assert d1 == d2
    assert d1.is_dir()


def test_resolve_base_dir_dev_mode() -> None:
    with patch.object(sys, "frozen", False, create=True):
        base = _resolve_base_dir()
        assert base.exists()


class TestFrozenMode:
    def test_resolve_base_dir_frozen(self, tmp_path: Path) -> None:
        fake_exe = tmp_path / "myapp.exe"
        fake_exe.write_text("fake")
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "executable", str(fake_exe)):
                base = _resolve_base_dir()
                assert base == tmp_path

    def test_setup_logging_frozen_mode(self, tmp_path: Path) -> None:
        fake_exe = tmp_path / "myapp.exe"
        fake_exe.write_text("fake")
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "executable", str(fake_exe)):
                log_path = setup_logging()
                assert log_path.parent == tmp_path / "logs"
                assert log_path.exists()
                # cleanup so test collection doesn't leak handlers
                for h in list(
                    logging.getLogger("devbase").handlers
                ):
                    h.close()
                    logging.getLogger("devbase").removeHandler(h)
