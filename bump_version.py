"""Synchronize and bump the DevBase project version."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

ROOT_DIR = Path(__file__).resolve().parent


class VersionSyncError(RuntimeError):
    """Raised when a version field is missing, ambiguous, or inconsistent."""


@dataclass(frozen=True, order=True, slots=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = re.fullmatch(
            r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0))?",
            value,
        )
        if match is None:
            raise VersionSyncError(f"invalid semantic version: {value!r}")
        return cls(*(int(part) for part in match.groups()[:3]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def windows_tuple(self) -> str:
        return f"({self.major}, {self.minor}, {self.patch}, 0)"

    def windows_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}.0"


def bump(version: Version, part: str) -> Version:
    if part == "patch":
        return Version(version.major, version.minor, version.patch + 1)
    if part == "minor":
        return Version(version.major, version.minor + 1, 0)
    if part == "major":
        return Version(version.major + 1, 0, 0)
    raise VersionSyncError(f"unknown bump part: {part!r}")


def _read(path: Path) -> str:
    if not path.is_file():
        raise VersionSyncError(f"missing version file: {path}")
    return path.read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.write_bytes(content.encode("utf-8"))


def _write_json(path: Path, data: object) -> None:
    original = path.read_bytes()
    newline = "\r\n" if b"\r\n" in original else "\n"
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if newline == "\r\n":
        content = content.replace("\n", "\r\n")
    path.write_bytes(content.encode("utf-8"))


def _replace_once(
    path: Path,
    pattern: str,
    replacement: str | Callable[[re.Match[str]], str],
) -> None:
    content = _read(path)
    matches = list(re.finditer(pattern, content, re.MULTILINE))
    if len(matches) != 1:
        raise VersionSyncError(
            f"expected exactly one version field in {path}, found {len(matches)}"
        )
    updated = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)
    _write(path, updated)


def _version_from_version_py(root: Path) -> Version:
    content = _read(root / "version.py")
    match = re.search(r"^__version__\s*=\s*[\"']([^\"']+)[\"']\s*$", content, re.MULTILINE)
    if match is None:
        raise VersionSyncError("version.py has no unique __version__ field")
    return Version.parse(match.group(1))


def _version_from_package(path: Path) -> Version:
    try:
        data = json.loads(_read(path))
        return Version.parse(data["version"])
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise VersionSyncError(f"invalid package version in {path}") from error


def _update_package_version(path: Path, version: Version) -> None:
    try:
        data = json.loads(_read(path))
        if not isinstance(data, dict) or "version" not in data:
            raise KeyError("version")
        data["version"] = str(version)
        _write_json(path, data)
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise VersionSyncError(f"invalid package version in {path}") from error


def _update_lock_version(path: Path, version: Version) -> None:
    try:
        data = json.loads(_read(path))
        root_package = data["packages"][""]
        data["version"] = str(version)
        root_package["version"] = str(version)
        _write_json(path, data)
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise VersionSyncError(f"invalid lock version in {path}") from error


def _version_from_lock(path: Path) -> Version:
    try:
        data = json.loads(_read(path))
        root_package = data["packages"][""]
        if data["version"] != root_package["version"]:
            raise VersionSyncError(f"lock root versions disagree in {path}")
        return Version.parse(root_package["version"])
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise VersionSyncError(f"invalid lock version in {path}") from error


def _version_from_version_info(path: Path) -> Version:
    content = _read(path)
    tuple_match = re.search(r"filevers=\((\d+),\s*(\d+),\s*(\d+),\s*\d+\)", content)
    string_match = re.search(r"StringStruct\('FileVersion',\s*'([^']+)'\)", content)
    product_match = re.search(r"StringStruct\('ProductVersion',\s*'([^']+)'\)", content)
    if tuple_match is None or string_match is None or product_match is None:
        raise VersionSyncError(f"version_info.txt has incomplete version fields")
    tuple_version = Version(
        int(tuple_match.group(1)),
        int(tuple_match.group(2)),
        int(tuple_match.group(3)),
    )
    if Version.parse(string_match.group(1)) != tuple_version:
        raise VersionSyncError("version_info.txt filevers and FileVersion disagree")
    if Version.parse(product_match.group(1)) != tuple_version:
        raise VersionSyncError("version_info.txt filevers and ProductVersion disagree")
    return tuple_version


def collect_versions(root: Path = ROOT_DIR) -> dict[str, Version]:
    return {
        "version.py": _version_from_version_py(root),
        "backend/pyproject.toml": _version_from_regex(
            root / "backend" / "pyproject.toml",
            r"^version\s*=\s*\"([^\"]+)\"\s*$",
        ),
        "backend/devbase/__init__.py": _version_from_regex(
            root / "backend" / "devbase" / "__init__.py",
            r"^__version__\s*=\s*\"([^\"]+)\"\s*$",
        ),
        "backend/devbase/api/app.py": _version_from_app(
            root / "backend" / "devbase" / "api" / "app.py",
            _version_from_version_py(root),
        ),
        "web/package.json": _version_from_package(root / "web" / "package.json"),
        "web/package-lock.json": _version_from_lock(
            root / "web" / "package-lock.json"
        ),
        "version_info.txt": _version_from_version_info(root / "version_info.txt"),
        "web/src/app/App.tsx": _version_from_regex(
            root / "web" / "src" / "app" / "App.tsx",
            r"<dt>版本</dt>\s*<dd>([^<]+)</dd>",
        ),
    }


def _version_from_regex(path: Path, pattern: str) -> Version:
    content = _read(path)
    matches = re.findall(pattern, content, re.MULTILINE)
    if len(matches) != 1:
        raise VersionSyncError(
            f"expected exactly one version field in {path}, found {len(matches)}"
        )
    return Version.parse(matches[0])


def _version_from_app(path: Path, canonical: Version) -> Version:
    content = _read(path)
    literal = re.findall(r"^\s*version=\"([^\"]+)\",\s*$", content, re.MULTILINE)
    reference = re.findall(r"^\s*version=__version__,\s*$", content, re.MULTILINE)
    if len(literal) == 1 and not reference:
        return Version.parse(literal[0])
    if not literal and len(reference) == 1:
        return canonical
    raise VersionSyncError(
        f"expected exactly one version field in {path}, found {len(literal) + len(reference)}"
    )


def check_consistency(root: Path = ROOT_DIR) -> list[str]:
    try:
        versions = collect_versions(root)
    except VersionSyncError as error:
        return [str(error)]
    expected = versions["version.py"]
    return [
        f"{path}: {version} != {expected}"
        for path, version in versions.items()
        if version != expected
    ]


def update_version(root: Path, version: Version) -> None:
    version_text = str(version)
    _replace_once(
        root / "version.py",
        r"^__version__\s*=\s*[\"'][^\"']+[\"']\s*$",
        f'__version__ = "{version_text}"',
    )
    _replace_once(
        root / "backend" / "pyproject.toml",
        r"^version\s*=\s*\"[^\"]+\"\s*$",
        f'version = "{version_text}"',
    )
    _replace_once(
        root / "backend" / "devbase" / "__init__.py",
        r"^__version__\s*=\s*\"[^\"]+\"\s*$",
        f'__version__ = "{version_text}"',
    )
    _replace_once(
        root / "backend" / "devbase" / "api" / "app.py",
        r"^\s*version=(?:\"[^\"]+\"|__version__),\s*$",
        "        version=__version__,",
    )
    _update_package_version(root / "web" / "package.json", version)
    _update_lock_version(root / "web" / "package-lock.json", version)
    _replace_once(
        root / "version_info.txt",
        r"filevers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)",
        f"filevers={version.windows_tuple()}",
    )
    _replace_once(
        root / "version_info.txt",
        r"prodvers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)",
        f"prodvers={version.windows_tuple()}",
    )
    _replace_once(
        root / "version_info.txt",
        r"StringStruct\('FileVersion',\s*'[^']+'\)",
        f"StringStruct('FileVersion', '{version.windows_string()}')",
    )
    _replace_once(
        root / "version_info.txt",
        r"StringStruct\('ProductVersion',\s*'[^']+'\)",
        f"StringStruct('ProductVersion', '{version.windows_string()}')",
    )
    _replace_once(
        root / "version_info.txt",
        r"StringStruct\('LegalCopyright',\s*'[^']+'\)",
        f"StringStruct('LegalCopyright', 'Copyright © SYNTEC {date.today().year}')",
    )
    _replace_once(
        root / "web" / "src" / "app" / "App.tsx",
        r"(<dt>版本</dt>\s*<dd>)[^<]+(</dd>)",
        lambda match: f"{match.group(1)}{version_text}{match.group(2)}",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("part", nargs="?", choices=("patch", "minor", "major"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="check only; never write")
    mode.add_argument(
        "--sync",
        action="store_true",
        help="write all targets using the current canonical version",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check and args.part is not None:
        raise SystemExit("--check does not accept a bump part")
    if args.sync and args.part is not None:
        raise SystemExit("--sync does not accept a bump part")

    try:
        current = _version_from_version_py(ROOT_DIR)
        if args.check:
            problems = check_consistency(ROOT_DIR)
            if problems:
                for problem in problems:
                    print(problem, file=sys.stderr)
                return 1
            print(f"version consistency OK: {current}")
            return 0
        if args.sync:
            update_version(ROOT_DIR, current)
            print(f"synchronized version: {current}")
            return 0
        if args.part is None:
            raise VersionSyncError("choose patch, minor, major, --sync, or --check")
        target = bump(current, args.part)
        update_version(ROOT_DIR, target)
        print(f"version: {current} -> {target}")
        return 0
    except VersionSyncError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
