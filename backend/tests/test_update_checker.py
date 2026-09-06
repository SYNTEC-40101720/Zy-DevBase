"""Offline tests for GitHub Release discovery and downloads."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from devbase.application.update_checker import (
    GitHubReleaseClient,
    ReleaseVersion,
    UpdateCheckError,
    UpdateConfig,
)


class FakeResponse:
    def __init__(self, payload: object = None, body: bytes = b"", headers=None):
        self.payload = payload
        self.body = io.BytesIO(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.body.read(size)

    def __iter__(self):
        return iter(())


def release_payload(
    tag: str,
    *,
    name: str = "SYNTEC_DevBase-1.2.0.zip",
    url: str = "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/download/v1.2.0/SYNTEC_DevBase-1.2.0.zip",
    digest: str | None = "0" * 64,
    draft: bool = False,
    prerelease: bool = False,
) -> dict:
    return {
        "tag_name": tag,
        "html_url": "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/tag/v1.2.0",
        "draft": draft,
        "prerelease": prerelease,
        "assets": [
            {
                "name": name,
                "browser_download_url": url,
                "size": 4,
                "digest": digest,
            }
        ],
    }


def opener_for(payload: dict, body: bytes = b""):
    def opener(_request, timeout):
        assert timeout > 0
        return FakeResponse(body=body, headers={"Content-Length": str(len(body))})

    response = FakeResponse(body=json.dumps(payload).encode("utf-8"))
    response.headers = {}

    def release_opener(_request, timeout):
        assert timeout > 0
        return response

    return release_opener


def test_release_version_compares_numerically() -> None:
    assert ReleaseVersion.parse("v1.10.0") > ReleaseVersion.parse("1.9.99")


def test_new_stable_release_is_available() -> None:
    client = GitHubReleaseClient(
        UpdateConfig(timeout_seconds=3),
        opener=opener_for(release_payload("v1.2.0")),
    )

    result = client.check("1.1.9")

    assert result.available is True
    assert result.installable is True
    assert result.release is not None
    assert result.release.asset.name == "SYNTEC_DevBase-1.2.0.zip"


@pytest.mark.parametrize("current", ["1.2.0", "1.3.0"])
def test_equal_or_newer_current_version_is_not_available(current: str) -> None:
    client = GitHubReleaseClient(
        UpdateConfig(timeout_seconds=3),
        opener=opener_for(release_payload("v1.2.0")),
    )
    result = client.check(current)
    assert result.available is False
    assert result.installable is False


def test_draft_release_is_not_installable() -> None:
    client = GitHubReleaseClient(
        opener=opener_for(release_payload("v1.2.0", draft=True))
    )
    result = client.check("1.0.0")
    assert result.error == "latest GitHub release is not stable"
    assert result.installable is False


def test_invalid_json_is_check_error() -> None:
    def opener(_request, timeout):
        return FakeResponse(body=b"not-json")

    result = GitHubReleaseClient(opener=opener).check("1.0.0")
    assert result.installable is False
    assert result.error


def test_wrong_asset_prefix_is_rejected() -> None:
    client = GitHubReleaseClient(
        opener=opener_for(release_payload("v1.2.0", name="other-1.2.0.zip"))
    )
    result = client.check("1.0.0")
    assert result.installable is False
    assert "matching release asset" in result.error


def test_wrong_download_host_is_rejected() -> None:
    client = GitHubReleaseClient(
        opener=opener_for(
            release_payload(
                "v1.2.0",
                url="https://example.com/download/SYNTEC_DevBase-1.2.0.zip",
            )
        )
    )
    result = client.check("1.0.0")
    assert result.installable is False
    assert "matching release asset" in result.error


def test_missing_digest_is_rejected() -> None:
    client = GitHubReleaseClient(
        opener=opener_for(release_payload("v1.2.0", digest=None))
    )

    result = client.check("1.0.0")

    assert result.installable is False
    assert result.error == "release asset is missing SHA-256 digest"


def test_download_streams_and_verifies_sha256(tmp_path: Path) -> None:
    body = b"zip-bytes"
    digest = hashlib.sha256(body).hexdigest()
    asset = GitHubReleaseClient(
        UpdateConfig(timeout_seconds=3),
        opener=lambda _request, timeout: FakeResponse(
            body=body,
            headers={"Content-Length": str(len(body))},
        ),
    )
    from devbase.application.update_checker import ReleaseAsset

    path = asset.download_asset(
        ReleaseAsset(
            "SYNTEC_DevBase-1.2.0.zip",
            "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/download/v1.2.0/SYNTEC_DevBase-1.2.0.zip",
            len(body),
            digest,
        ),
        tmp_path,
    )
    assert path.read_bytes() == body


def test_download_digest_mismatch_removes_temp_file(tmp_path: Path) -> None:
    body = b"zip-bytes"
    client = GitHubReleaseClient(
        opener=lambda _request, timeout: FakeResponse(body=body),
    )
    from devbase.application.update_checker import ReleaseAsset

    with pytest.raises(UpdateCheckError, match="mismatch"):
        client.download_asset(
            ReleaseAsset(
                "SYNTEC_DevBase-1.2.0.zip",
                "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/download/v1.2.0/SYNTEC_DevBase-1.2.0.zip",
                len(body),
                "0" * 64,
            ),
            tmp_path,
        )
    assert list(tmp_path.glob("download-*.zip")) == []


def test_empty_download_rejected(tmp_path: Path) -> None:
    client = GitHubReleaseClient(opener=lambda _request, timeout: FakeResponse())
    from devbase.application.update_checker import ReleaseAsset

    with pytest.raises(UpdateCheckError, match="empty"):
        client.download_asset(
            ReleaseAsset(
                "SYNTEC_DevBase-1.2.0.zip",
                "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/download/v1.2.0/SYNTEC_DevBase-1.2.0.zip",
                0,
                hashlib.sha256(b"").hexdigest(),
            ),
            tmp_path,
        )


def test_update_config_default_timeout_is_60s() -> None:
    assert UpdateConfig().timeout_seconds == 60.0


def test_update_config_from_environment_overrides_timeout(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_UPDATE_TIMEOUT", "120")
    assert UpdateConfig.from_environment().timeout_seconds == 120.0


def test_update_config_from_environment_overrides_max_bytes(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_UPDATE_MAX_BYTES", str(10 * 1024 * 1024))
    assert UpdateConfig.from_environment().max_download_bytes == 10 * 1024 * 1024


def test_update_config_from_environment_falls_back_on_garbage(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_UPDATE_TIMEOUT", "garbage")
    monkeypatch.setenv("PLATFORM_UPDATE_MAX_BYTES", "not-a-number")
    config = UpdateConfig.from_environment()
    assert config.timeout_seconds == 60.0
    assert config.max_download_bytes == 512 * 1024 * 1024


def test_update_config_from_environment_rejects_below_floor(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_UPDATE_TIMEOUT", "1")
    monkeypatch.setenv("PLATFORM_UPDATE_MAX_BYTES", "1024")
    config = UpdateConfig.from_environment()
    assert config.timeout_seconds == 60.0
    assert config.max_download_bytes == 512 * 1024 * 1024
