"""Long-lived interactive calculator session — the CalcManager analog.

Borrowed from Microsoft Calculator's ``CCalcManager``: a long-lived object
that owns the engine and the display sink, and accepts a stream of key
presses. Unlike the one-shot ``JobRuntime``, a session is interactive —
each ``press`` mutates state and returns the new view. It never spawns a
thread; the engine is synchronous and pushes state through the sink.

The session is the application-layer adapter: the pure domain engine
declares the ``DisplaySink`` port, this module implements it.
"""

from __future__ import annotations

from typing import Any

from platform_runtime.domain.calculator import CalcKey, CalculatorEngine

from .display import CalculatorDisplay


class CalculatorSession:
    """Owns a :class:`CalculatorEngine` and its :class:`CalculatorDisplay`."""

    def __init__(self, *, history_limit: int = 512) -> None:
        self._display = CalculatorDisplay()
        self._engine = CalculatorEngine(self._display, history_limit=history_limit)

    def press(self, key: str) -> dict[str, Any]:
        """Apply one key string; return the new view snapshot."""
        self._engine.press(CalcKey(key))
        return self.view()

    def view(self) -> dict[str, Any]:
        """Return the current rendered view (display, expression, history...)."""
        return self._display.view()

    def clear(self) -> dict[str, Any]:
        """Convenience: full reset (memory kept, per engine behavior)."""
        self._engine.press(CalcKey.CLEAR)
        return self.view()
