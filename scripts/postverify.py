"""Verify a PyInstaller one-directory SYNTEC release bundle."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class PostverifyError(RuntimeError):
    """Raised when a packaged bundle fails release validation."""


def _find_executable(bundle_dir: Path, executable_name: str) -> Path:
    candidates = [bundle_dir / executable_name]
    candidates = [path for path in candidates if path.is_file()]
    if len(candidates) != 1:
        raise PostverifyError(
            f"expected exactly one SYNTEC exe in {bundle_dir}, found {len(candidates)}"
        )
    return candidates[0]


def _check_internal_files(bundle_dir: Path) -> None:
    internal = bundle_dir / "_internal"
    search_root = internal if internal.is_dir() else bundle_dir
    has_python_dll = any(search_root.glob("python*.dll"))
    has_archive = (search_root / "base_library.zip").is_file()
    if not has_python_dll or not has_archive:
        raise PostverifyError(
            "bundle is missing PyInstaller internal files "
            "(python*.dll and base_library.zip)"
        )


def _read_windows_version_info(exe: Path) -> dict[str, object]:
    if sys.platform != "win32":
        raise PostverifyError("Windows version metadata requires a Windows verifier")
    escaped = str(exe).replace("'", "''")
    command = (
        f"$v=(Get-Item -LiteralPath '{escaped}').VersionInfo; "
        "$v | Select-Object CompanyName,LegalCopyright,FileVersion,"
        "ProductVersion,ProductName,FileDescription,Language | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PostverifyError(result.stderr.strip() or "could not read exe version info")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise PostverifyError("PowerShell returned invalid version metadata") from error


def _check_metadata(metadata: dict[str, object]) -> None:
    company = str(metadata.get("CompanyName", ""))
    copyright_text = str(metadata.get("LegalCopyright", ""))
    file_version = str(metadata.get("FileVersion", ""))
    product_version = str(metadata.get("ProductVersion", ""))
    if "SYNTEC" not in company.upper():
        raise PostverifyError("exe CompanyName must contain SYNTEC")
    if "SYNTEC" not in copyright_text.upper():
        raise PostverifyError("exe LegalCopyright must contain SYNTEC")
    if str(date.today().year) not in copyright_text:
        raise PostverifyError("exe LegalCopyright must contain the release year")
    for name, value in (("FileVersion", file_version), ("ProductVersion", product_version)):
        if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", value) is None:
            raise PostverifyError(f"exe {name} must have four numeric components")


def verify_bundle(
    bundle_dir: Path,
    executable_name: str = "SYNTEC_DevBase.exe",
) -> Path:
    if not bundle_dir.is_dir():
        raise PostverifyError(f"missing bundle directory: {bundle_dir}")
    executable = _find_executable(bundle_dir, executable_name)
    _check_internal_files(bundle_dir)
    _check_metadata(_read_windows_version_info(executable))
    return executable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=ROOT_DIR / "dist" / "SYNTEC_DevBase",
    )
    parser.add_argument("--executable-name", default="SYNTEC_DevBase.exe")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        executable = verify_bundle(args.bundle_dir, args.executable_name)
    except PostverifyError as error:
        print(f"postverify: {error}", file=sys.stderr)
        return 1
    print(f"postverify OK: {executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
