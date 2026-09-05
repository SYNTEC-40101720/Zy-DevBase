"""Preflight checks for SYNTEC domain-controlled packaging."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bump_version import check_consistency  # noqa: E402


class PrecheckError(RuntimeError):
    """Raised when packaging prerequisites are not satisfied."""


def _check_english_path(root: Path) -> None:
    path_text = str(root.resolve())
    if re.search(r"[^A-Za-z0-9_:/\\.\-]", path_text):
        raise PrecheckError(
            f"packaging path must be pure English without spaces: {path_text}"
        )


def _check_version(root: Path) -> None:
    problems = check_consistency(root)
    if problems:
        raise PrecheckError("version metadata is inconsistent: " + "; ".join(problems))


def _check_frontend(root: Path) -> None:
    index = root / "web" / "dist" / "index.html"
    if not index.is_file():
        raise PrecheckError(
            f"missing frontend build entry: {index}; run npm run build first"
        )


def _check_spec(root: Path) -> None:
    content = (root / "devbase.spec").read_text(encoding="utf-8")
    if "upx=True" in content:
        raise PrecheckError("devbase.spec must disable UPX")
    if re.search(r'name\s*=\s*["\']SYNTEC', content) is None:
        raise PrecheckError("PyInstaller output name must start with SYNTEC")


def _check_version_resource(root: Path) -> None:
    content = (root / "version_info.txt").read_text(encoding="utf-8")
    required = (
        "'000004B0'",
        "StringStruct('CompanyName', 'SYNTEC')",
        "StringStruct('LegalCopyright', 'Copyright © SYNTEC ",
        "VarStruct('Translation', [0, 1200])",
    )
    missing = [item for item in required if item not in content]
    if missing:
        raise PrecheckError(
            "version_info.txt is missing SYNTEC metadata: " + ", ".join(missing)
        )
    for field in ("FileVersion", "ProductVersion"):
        if re.search(rf"StringStruct\('{field}', '\d+\.\d+\.\d+\.\d+'\)", content) is None:
            raise PrecheckError(f"{field} must contain four numeric components")


def run_precheck(root: Path = ROOT_DIR) -> list[str]:
    checks = (
        _check_english_path,
        _check_version,
        _check_frontend,
        _check_spec,
        _check_version_resource,
    )
    errors: list[str] = []
    for check in checks:
        try:
            check(root)
        except (OSError, PrecheckError) as error:
            errors.append(str(error))
    return errors


def main() -> int:
    errors = run_precheck()
    if errors:
        for error in errors:
            print(f"precheck: {error}", file=sys.stderr)
        return 1
    print("precheck OK: SYNTEC packaging prerequisites satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
