"""Host implementation of the calculator :class:`DisplaySink`.

Borrowed from Microsoft Calculator's ``CalculatorDisplay`` (the C++/WinRT
client of ``ICalcDisplay``): the engine pushes state through this sink; it
records the latest view so the API/session can snapshot it. It owns no
logic — it is a passive renderer of what the engine tells it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from platform_runtime.domain.ports import DisplaySink


@dataclass(slots=True)
class CalculatorDisplay(DisplaySink):
    """Records the latest display/expression/memory/history/error state."""

    primary: str = "0"
    is_error: bool = False
    tokens: tuple[str, ...] = ()
    memory: tuple[str, ...] = ()
    history: list[tuple[str, str]] = field(default_factory=list)

    def set_primary(self, value: str, *, is_error: bool = False) -> None:
        self.primary = value
        self.is_error = is_error

    def set_expression(self, tokens: tuple[str, ...]) -> None:
        self.tokens = tokens

    def set_memory(self, slots: tuple[str, ...]) -> None:
        self.memory = slots

    def add_history(self, expression: str, result: str) -> int:
        self.history.append((expression, result))
        return len(self.history) - 1

    def set_error(self, is_error: bool) -> None:
        self.is_error = is_error

    def view(self) -> dict[str, object]:
        """JSON-serializable snapshot of the rendered view."""
        return {
            "display": self.primary,
            "expression": list(self.tokens),
            "error": self.is_error,
            "memory": list(self.memory),
            "history": [{"expression": e, "result": r} for e, r in self.history],
        }
