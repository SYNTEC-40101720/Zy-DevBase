"""Default, business-neutral configuration template."""

from __future__ import annotations

DEFAULT_CONFIG: dict[str, dict[str, str]] = {
    "app": {
        "name": "DevBase",
        "config_version": "1",
    }
}


def default_values() -> dict[str, dict[str, str]]:
    """Return a mutable shallow copy of the default [app] template."""
    return {k: dict(v) for k, v in DEFAULT_CONFIG.items()}


__all__ = ["DEFAULT_CONFIG", "default_values"]
