"""Domain ports — the contracts an engine declares it needs.

Borrowed from Microsoft Calculator's ``ICalcDisplay`` / ``IHistoryDisplay``:
the *engine* (domain) declares what it needs as abstract ports, the
*host* (application) implements them. This is inversion of control — the
domain never imports FastAPI, threading, or any framework; it only
describes the holes a host must fill.

Two port families live here:

* :class:`ProgressSink` — the minimal port a one-shot task uses
  (report a 0..1 progress + message, observe cancellation). ``TaskContext``
  in the application layer implements it.
* :class:`DisplaySink` — the richer port an *interactive* tool uses
  (calculator-style: primary display, expression tokens, memory slots,
  history items, error flag). The calculator engine (phase 2) will
  declare this port; the application layer implements it.

Both are :class:`typing.Protocol` (structural): any object with the right
methods satisfies them — no inheritance required.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressSink(Protocol):
    """Minimal port for a one-shot background task.

    The runtime owns a concrete implementation (``TaskContext``) and passes
    it in; task bodies only call :meth:`report_progress` and
    :meth:`is_cancelled`.
    """

    def report_progress(self, progress: float, message: str = "") -> None:
        """Report progress in ``[0.0, 1.0]`` and an optional human message."""
        ...

    def is_cancelled(self) -> bool:
        """True if the host requested cancellation."""
        ...


@runtime_checkable
class DisplaySink(Protocol):
    """Port for an interactive, calculator-style engine.

    Mirrors ``ICalcDisplay`` + ``IHistoryDisplay``: the engine pushes
    display state, expression tokens, memory, and history through this
    sink; the host renders it. Phase 2 (calculator) consumes this.
    """

    def set_primary(self, value: str, *, is_error: bool = False) -> None:
        """Set the primary display value (and error flag)."""
        ...

    def set_expression(self, tokens: tuple[str, ...]) -> None:
        """Set the expression preview as ordered tokens."""
        ...

    def set_memory(self, slots: tuple[str, ...]) -> None:
        """Set the full memory-slot list (one string each)."""
        ...

    def add_history(self, expression: str, result: str) -> int:
        """Append a history item; return its index."""
        ...

    def set_error(self, is_error: bool) -> None:
        """Toggle the error indicator."""
        ...


__all__ = ["ProgressSink", "DisplaySink"]
