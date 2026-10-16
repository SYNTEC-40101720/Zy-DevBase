"""Optional, read-only discovery of the latest stable GitHub Release."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class UpdateCheckError(RuntimeError):
    """Raised for malformed or unsafe release metadata."""


@dataclass(frozen=True, order=True, slots=True)
class ReleaseVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "ReleaseVersion":
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
        if match is None:
            raise UpdateCheckError(f"invalid release version: {value!r}")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class UpdateConfig:
    owner: str = "SYNTEC-40101720"
    repository: str = "Zy-DevBase"
    timeout_seconds: float = 5.0

    @classmethod
    def from_environment(cls) -> "UpdateConfig":
        """Accept a finite 1..30 second metadata request timeout."""
        raw = os.getenv("PLATFORM_UPDATE_TIMEOUT")
        try:
            timeout = float(raw) if raw is not None else cls().timeout_seconds
        except ValueError:
            return cls()
        if not math.isfinite(timeout) or not 1 <= timeout <= 30:
            return cls()
        return replace(cls(), timeout_seconds=timeout)

    @property
    def api_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repository}/releases/latest"

    @property
    def release_prefix(self) -> str:
        return f"https://github.com/{self.owner}/{self.repository}/releases/tag/"


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    tag_name: str
    version: ReleaseVersion
    html_url: str


@dataclass(frozen=True, slots=True)
class UpdateCheckResult:
    current: ReleaseVersion
    latest: ReleaseVersion | None
    available: bool
    release: ReleaseInfo | None = None
    error: str | None = None


Opener = Callable[..., Any]


class GitHubReleaseClient:
    """Check metadata on demand; never download, install, or retry."""

    def __init__(
        self,
        config: UpdateConfig | None = None,
        *,
        opener: Opener = urlopen,
    ) -> None:
        self.config = config or UpdateConfig()
        self._opener = opener

    def check(self, current: str | ReleaseVersion) -> UpdateCheckResult:
        current_version = (
            current if isinstance(current, ReleaseVersion) else ReleaseVersion.parse(current)
        )
        try:
            release = self._parse_release(self._fetch_release())
        except (OSError, URLError, ValueError, TypeError, KeyError, UpdateCheckError) as error:
            return UpdateCheckResult(
                current=current_version,
                latest=None,
                available=False,
                error=str(error) or "update check did not complete",
            )
        return UpdateCheckResult(
            current=current_version,
            latest=release.version,
            available=release.version > current_version,
            release=release,
        )

    def _fetch_release(self) -> dict[str, Any]:
        request = Request(
            self.config.api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Zy-DevBase-version-check",
            },
        )
        with self._opener(request, timeout=self.config.timeout_seconds) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise UpdateCheckError("GitHub release response is not an object")
        return payload

    def _parse_release(self, payload: dict[str, Any]) -> ReleaseInfo:
        if payload.get("draft") or payload.get("prerelease"):
            raise UpdateCheckError("latest GitHub release is not stable")
        tag_name = payload.get("tag_name")
        html_url = payload.get("html_url")
        if not isinstance(tag_name, str) or not isinstance(html_url, str):
            raise UpdateCheckError("release is missing tag_name or html_url")
        version = ReleaseVersion.parse(tag_name)
        if tag_name not in (str(version), f"v{version}"):
            raise UpdateCheckError("release tag is not canonical")
        if html_url != f"{self.config.release_prefix}{tag_name}":
            raise UpdateCheckError("release URL must point to this repository's HTTPS release page")
        return ReleaseInfo(tag_name, version, html_url)


__all__ = [
    "GitHubReleaseClient",
    "ReleaseInfo",
    "ReleaseVersion",
    "UpdateCheckError",
    "UpdateCheckResult",
    "UpdateConfig",
]
