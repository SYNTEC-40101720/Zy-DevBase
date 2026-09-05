"""Tests for DPAPI and the explicit non-secure test fallback."""

from __future__ import annotations

import sys

import pytest

from devbase.secret_store import (
    DPAPI_PREFIX,
    INSECURE_PREFIX,
    SecretStore,
    SecretStoreError,
    SecretStoreUnavailableError,
)


def test_plain_values_are_left_unchanged() -> None:
    assert SecretStore().unprotect("plain-value") == "plain-value"


def test_windows_dpapi_round_trip_or_explicit_fallback() -> None:
    if sys.platform == "win32":
        store = SecretStore()
        protected = store.protect("unit-test-secret")
        assert protected.startswith(DPAPI_PREFIX)
        assert store.unprotect(protected) == "unit-test-secret"
    else:
        store = SecretStore(
            allow_insecure_fallback=True,
            platform="linux",
        )
        with pytest.warns(RuntimeWarning, match="insecure"):
            protected = store.protect("unit-test-secret")
        assert protected.startswith(INSECURE_PREFIX)
        assert store.unprotect(protected) == "unit-test-secret"


def test_non_windows_requires_explicit_fallback() -> None:
    store = SecretStore(platform="linux")
    with pytest.raises(SecretStoreUnavailableError, match="DPAPI"):
        store.protect("unit-test-secret")


def test_insecure_prefix_requires_explicit_fallback() -> None:
    fallback = SecretStore(
        allow_insecure_fallback=True,
        platform="linux",
    )
    with pytest.warns(RuntimeWarning):
        protected = fallback.protect("unit-test-secret")

    with pytest.raises(SecretStoreUnavailableError, match="explicit"):
        SecretStore(platform="linux").unprotect(protected)


def test_invalid_protected_encoding_raises() -> None:
    with pytest.raises(SecretStoreError, match="encoding"):
        SecretStore().unprotect(f"{DPAPI_PREFIX}not-base64!")


def test_unknown_prefix_is_not_treated_as_secret() -> None:
    assert SecretStore().unprotect("other:value") == "other:value"
