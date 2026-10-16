"""Offline tests for read-only GitHub Release discovery."""

from __future__ import annotations

import io
import json
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from devbase.application.update_checker import (
    GitHubReleaseClient,
    ReleaseVersion,
    UpdateConfig,
)

RELEASE_URL = "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/tag/v1.2.0"


def release_payload(**overrides) -> dict:
    return {
        "tag_name": "v1.2.0",
        "html_url": RELEASE_URL,
        "draft": False,
        "prerelease": False,
        **overrides,
    }


def opener_for(payload):
    def opener(_request, timeout):
        assert timeout > 0
        return io.BytesIO(json.dumps(payload).encode("utf-8"))
    return opener


def test_release_version_compares_numerically() -> None:
    assert ReleaseVersion.parse("v1.10.0") > ReleaseVersion.parse("1.9.99")


def test_new_release_needs_no_asset_or_digest() -> None:
    result = GitHubReleaseClient(opener=opener_for(release_payload())).check("1.1.9")
    assert result.available is True
    assert result.error is None
    assert result.release.html_url == RELEASE_URL
    assert str(result.latest) == "1.2.0"


@pytest.mark.parametrize("assets", [[], None, [{"digest": None}], "invalid"])
def test_asset_metadata_is_not_needed_for_notification(assets) -> None:
    result = GitHubReleaseClient(
        opener=opener_for(release_payload(assets=assets)),
    ).check("1.0.0")
    assert result.available is True
    assert result.error is None


@pytest.mark.parametrize("current", ["1.2.0", "1.3.0"])
def test_equal_or_newer_current_version_is_not_available(current: str) -> None:
    result = GitHubReleaseClient(opener=opener_for(release_payload())).check(current)
    assert result.available is False
    assert result.error is None


@pytest.mark.parametrize("payload", [
    release_payload(draft=True),
    release_payload(prerelease=True),
    release_payload(tag_name="v1.2.0-rc.1"),
    release_payload(tag_name="invalid"),
    release_payload(tag_name="v01.2.0"),
    release_payload(html_url="http://github.com/SYNTEC-40101720/Zy-DevBase/releases/tag/v1.2.0"),
    release_payload(html_url="https://example.com/releases/tag/v1.2.0"),
    release_payload(html_url="https://github.com/other/repo/releases/tag/v1.2.0"),
    release_payload(html_url=RELEASE_URL + "?redirect=example.com"),
    release_payload(html_url=RELEASE_URL.replace("v1.2.0", "v1.1.0")),
    release_payload(html_url=None),
    [],
])
def test_invalid_metadata_is_incomplete_not_up_to_date(payload) -> None:
    result = GitHubReleaseClient(opener=opener_for(payload)).check("1.0.0")
    assert result.error
    assert result.latest is None
    assert result.available is False
    assert result.release is None


@pytest.mark.parametrize("error", [
    TimeoutError(),
    URLError("offline"),
    HTTPError("https://api.github.com/", 403, "rate limited", Message(), None),
    HTTPError("https://api.github.com/", 404, "not found or private", Message(), None),
])
def test_network_failure_is_nonfatal_and_not_retried(error) -> None:
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        raise error

    result = GitHubReleaseClient(opener=opener).check("1.0.0")
    assert len(calls) == 1
    assert result.error
    assert result.latest is None
    assert result.available is False


def test_invalid_json_is_check_error() -> None:
    result = GitHubReleaseClient(
        opener=lambda _request, timeout: io.BytesIO(b"not-json"),
    ).check("1.0.0")
    assert result.error


def test_metadata_request_has_short_timeout_and_no_side_effects(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, request.get_method(), timeout))
        return io.BytesIO(json.dumps(release_payload()).encode("utf-8"))

    client = GitHubReleaseClient(opener=opener)
    assert calls == []  # Constructing the app's client never contacts GitHub.
    assert client.check("1.0.0").available
    assert calls == [(UpdateConfig().api_url, "GET", 5.0)]
    assert list(tmp_path.iterdir()) == []
    assert not hasattr(client, "download_asset")


@pytest.mark.parametrize("value,expected", [
    ("1", 1.0), ("10", 10.0), ("30", 30.0),
    ("garbage", 5.0), ("0", 5.0), ("-1", 5.0), ("31", 5.0),
    ("nan", 5.0), ("inf", 5.0), ("-inf", 5.0),
])
def test_timeout_environment_is_bounded(monkeypatch, value, expected) -> None:
    monkeypatch.setenv("PLATFORM_UPDATE_TIMEOUT", value)
    assert UpdateConfig.from_environment().timeout_seconds == expected


def test_timeout_default_and_removed_download_options(monkeypatch) -> None:
    monkeypatch.delenv("PLATFORM_UPDATE_TIMEOUT", raising=False)
    monkeypatch.setenv("PLATFORM_UPDATE_MAX_BYTES", "1024")
    config = UpdateConfig.from_environment()
    assert config.timeout_seconds == 5.0
    assert not hasattr(config, "max_download_bytes")
