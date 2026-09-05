"""Tests for the top-level launcher entry point in ``main.py``.

These tests import the root ``main`` module by adding the project root to
``sys.path``; they cover argument parsing, frontend-build checks, browser-mode
flag combinations, and URL/helpers without starting a real server or window.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from threading import Event

import pytest

# The project root (parent of backend/) contains main.py.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

main_module = importlib.import_module("main")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_defaults(self) -> None:
        parser = main_module.build_parser()
        args = parser.parse_args([])
        assert args.browser is False
        assert args.desktop is False
        assert args.reload is False
        assert args.no_browser is False
        assert args.port == 8000

    def test_browser_flag(self) -> None:
        args = main_module.build_parser().parse_args(["--browser"])
        assert args.browser is True

    def test_no_browser_flag(self) -> None:
        args = main_module.build_parser().parse_args(
            ["--browser", "--no-browser"]
        )
        assert args.no_browser is True
        assert args.browser is True

    def test_host_and_port(self) -> None:
        args = main_module.build_parser().parse_args(
            ["--host", "example.local", "--port", "9999"]
        )
        assert args.host == "example.local"
        assert args.port == 9999

    def test_port_invalid_exits(self) -> None:
        parser = main_module.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--port", "not-a-number"])

    def test_env_port_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PLATFORM_PORT", "9000")
        args = main_module.build_parser().parse_args([])
        assert args.port == 9000

    def test_env_host_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PLATFORM_HOST", "custom.host")
        args = main_module.build_parser().parse_args([])
        assert args.host == "custom.host"

    def test_browser_and_desktop_mutually_exclusive(self) -> None:
        parser = main_module.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--browser", "--desktop"])


# ---------------------------------------------------------------------------
# Frontend build check
# ---------------------------------------------------------------------------

class TestRequireFrontendBuild:
    def test_present(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        index = tmp_path / "index.html"
        index.write_text("<html></html>", encoding="utf-8")
        monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", tmp_path)

        result = main_module._require_frontend_build()
        assert result == tmp_path

    def test_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", tmp_path)
        with pytest.raises(FileNotFoundError, match="index.html"):
            main_module._require_frontend_build()


# ---------------------------------------------------------------------------
# reload + browser combination validation
# ---------------------------------------------------------------------------

def test_reload_without_browser_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--reload`` without ``--browser`` should exit with a parser error."""
    monkeypatch.setattr(sys, "argv", ["prog", "--reload"])
    monkeypatch.setattr(
        main_module, "_require_frontend_build", lambda: Path(".")
    )
    with pytest.raises(SystemExit):
        main_module.main()


# ---------------------------------------------------------------------------
# host/url helpers
# ---------------------------------------------------------------------------

class TestHostHelpers:
    def test_local_host_passthrough(self) -> None:
        assert main_module._local_host("example.local") == "example.local"

    def test_local_host_colon_maps_to_default(self) -> None:
        # "::" should map to the same value as the default host
        default_host = main_module.build_parser().parse_args([]).host
        assert main_module._local_host("::") == main_module._local_host(
            default_host
        )

    def test_format_url_host_plain(self) -> None:
        assert main_module._format_url_host("example.local") == "example.local"

    def test_format_url_host_ipv6_brackets(self) -> None:
        # IPv6 addresses contain ':' and should be bracketed
        assert main_module._format_url_host("::1") == "[::1]"

    def test_browser_url(self) -> None:
        url = main_module._browser_url("example.local", 8000)
        assert url == "http://example.local:8000/"

    def test_browser_url_carries_local_token(self) -> None:
        url = main_module._browser_url("example.local", 8000, "local-token")
        assert url == "http://example.local:8000/?token=local-token"


# ---------------------------------------------------------------------------
# Server readiness logic
# ---------------------------------------------------------------------------

class TestWaitForServerReady:
    def test_returns_true_when_200(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_wait_for_server_ready returns True on HTTP 200."""

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(url, timeout):
            return FakeResponse()

        monkeypatch.setattr(main_module, "urlopen", fake_urlopen)
        stop = Event()
        assert (
            main_module._wait_for_server_ready("example.local", 8000, stop)
            is True
        )

    def test_timeout_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_wait_for_server_ready returns False on timeout."""
        from urllib.error import URLError

        def always_fail(url, timeout):
            raise URLError("no server")

        monkeypatch.setattr(main_module, "urlopen", always_fail)
        stop = Event()
        assert (
            main_module._wait_for_server_ready(
                "example.local", 8000, stop, timeout=0.01
            )
            is False
        )


# ---------------------------------------------------------------------------
# Browser-opener behavior
# ---------------------------------------------------------------------------

def test_open_browser_when_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """If server is ready, webbrowser.open should be called with the URL."""
    monkeypatch.setattr(
        main_module, "_wait_for_server_ready", lambda *a, **kw: True
    )
    opened: list[str] = []
    monkeypatch.setattr(main_module.webbrowser, "open", opened.append)
    stop = Event()
    main_module._open_browser_when_ready("example.local", 8765, stop)
    assert opened == ["http://example.local:8765/"]


def test_open_browser_not_called_when_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If server is not ready, browser should not be opened."""
    monkeypatch.setattr(
        main_module, "_wait_for_server_ready", lambda *a, **kw: False
    )
    opened: list[str] = []
    monkeypatch.setattr(main_module.webbrowser, "open", opened.append)
    stop = Event()
    main_module._open_browser_when_ready("example.local", 8765, stop)
    assert opened == []


# ---------------------------------------------------------------------------
# main() integration: missing frontend
# ---------------------------------------------------------------------------

def test_main_missing_frontend_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """main() should exit with code 1 when frontend build is missing."""
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        main_module.main()
    assert exc_info.value.code == 1
