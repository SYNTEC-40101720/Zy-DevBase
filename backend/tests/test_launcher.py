"""Tests for the top-level launcher entry point in ``main.py``.

main.py is now a no-argument entry: ``python main.py`` starts the desktop
window directly. These tests cover the frontend-build check and the
missing-frontend exit path without starting a real server or window.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# The project root (parent of backend/) contains main.py.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

main_module = importlib.import_module("main")


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
# main() integration: missing frontend
# ---------------------------------------------------------------------------

def test_main_missing_frontend_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """main() should raise FileNotFoundError when frontend build is missing."""
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="index.html"):
        main_module.main()
