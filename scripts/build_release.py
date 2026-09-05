"""Orchestrate frontend build, PyInstaller packaging, verification, and archive."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path = ROOT_DIR) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def version_text() -> str:
    namespace: dict[str, object] = {}
    exec((ROOT_DIR / "version.py").read_text(encoding="utf-8"), namespace)
    return str(namespace["__version__"])


def zip_bundle(bundle_dir: Path, output_dir: Path, version: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"SYNTEC_DevBase-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_file():
                target.write(path, path.relative_to(bundle_dir.parent))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return archive, checksum


def build_release(output_dir: Path) -> tuple[Path, Path]:
    run([sys.executable, str(ROOT_DIR / "scripts" / "precheck.py")])
    npm = "npm.cmd" if os.name == "nt" else "npm"
    run([npm, "run", "build"], cwd=ROOT_DIR / "web")
    run([
        sys.executable,
        "-m",
        "PyInstaller",
        "devbase.spec",
        "--noconfirm",
        "--clean",
    ])
    run([
        sys.executable,
        "-m",
        "PyInstaller",
        "devbase_updater.spec",
        "--noconfirm",
        "--clean",
    ])
    bundle_dir = ROOT_DIR / "dist" / "SYNTEC_DevBase"
    updater_bundle = ROOT_DIR / "dist" / "SYNTEC_DevBase-updater"
    run([
        sys.executable,
        str(ROOT_DIR / "scripts" / "postverify.py"),
        "--bundle-dir",
        str(bundle_dir),
    ])
    run([
        sys.executable,
        str(ROOT_DIR / "scripts" / "postverify.py"),
        "--bundle-dir",
        str(updater_bundle),
        "--executable-name",
        "SYNTEC_DevBase-updater.exe",
    ])
    shutil.copy2(
        updater_bundle / "SYNTEC_DevBase-updater.exe",
        bundle_dir / "SYNTEC_DevBase-updater.exe",
    )
    shutil.copytree(
        updater_bundle / "_internal",
        bundle_dir / "_internal",
        dirs_exist_ok=True,
    )
    return zip_bundle(bundle_dir, output_dir, version_text())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "release",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    archive, checksum = build_release(args.output_dir)
    print(f"release archive: {archive}")
    print(f"sha256 file: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
