"""Helpers for building URLs to the local application."""

from __future__ import annotations

from urllib.parse import urlencode


def format_url_host(host: str) -> str:
    local_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    if ":" in local_host and not local_host.startswith("["):
        return f"[{local_host}]"
    return local_host


def build_local_url(host: str, port: int, token: str | None = None) -> str:
    url = f"http://{format_url_host(host)}:{port}/"
    if token:
        url += "?" + urlencode({"token": token})
    return url


__all__ = ["build_local_url", "format_url_host"]