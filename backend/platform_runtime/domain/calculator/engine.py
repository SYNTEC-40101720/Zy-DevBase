"""Standard calculator engine — pure domain, no framework deps.

Borrowed from Microsoft Calculator's ``CCalcEngine`` (CalcManager): the
engine owns operand/operator state and a history collector, and pushes
display updates through a :class:`DisplaySink` port that the host
implements. It never imports FastAPI, threading, or any UI; it is fully
unit-testable with a fake sink.

Standard-mode behavior, modeled on Windows Calculator:

* digits build the current entry (replace-then-append, single decimal
  point, capped digit count);
* a binary operator stores the operand and the pending operator; a second
  operator *evaluates* the pending one first (chained calc);
* ``=`` evaluates the pending operator, appends a history line, and
  freezes the result as the new entry;
* unary ops (``sqrt``, ``x²``, ``1/x``, ``+/-``, ``%``) act on the current entry;
* memory ops (``MC``/``MR``/``M+``/``M-``/``MS``) maintain one slot and
  are reflected through ``sink.set_memory``;
* ``C`` clears state (memory kept); ``CE`` clears the current entry;
* division by zero (and invalid sqrt) sets the error flag — further input
  is ignored until ``C``/``CE``.

All numeric work uses :class:`decimal.Decimal` for precision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, DivisionByZero, InvalidOperation, getcontext

from ..ports import DisplaySink
from .keys import BINARY_OPS, DIGITS, CalcKey

# Engine-level display limits (mirrors CCalcEngine's max digit notion).
_MAX_DIGITS = 16
_Q = Decimal("0")


def _fmt(value: Decimal) -> str:
    """Render a Decimal as a plain calculator display string."""
    if value == value.to_integral_value():
        # drop the trailing .0 from integral results
        return str(value.to_integral_value())
    # strip insignificant trailing zeros, keep sign
    return format(value.normalize(), "f")


@dataclass(slots=True)
class _History:
    """In-memory equation history, capped to ``limit`` items."""

    limit: int = 512
    items: list[tuple[str, str]] = field(default_factory=list)

    def add(self, expression: str, result: str) -> int:
        self.items.append((expression, result))
        if len(self.items) > self.limit:
            self.items = self.items[-self.limit:]
        return len(self.items) - 1


class CalculatorEngine:
    """Standard calculator engine; pushes state through a ``DisplaySink``.

    Construct with a :class:`DisplaySink` (the host's implementation of
    the ``ICalcDisplay`` analog) and call :meth:`press` with a
    :class:`CalcKey`. The engine is the single source of truth; the sink
    only renders what it is told.
    """

    def __init__(self, sink: DisplaySink, *, history_limit: int = 512) -> None:
        getcontext().prec = 34
        self._sink = sink
        self._history = _History(limit=history_limit)

        # live state
        self._display: str = "0"
        self._accumulator: Decimal = _Q        # left operand of pending op
        self._pending_op: CalcKey | None = None
        self._entering: bool = True            # next digit replaces display
        self._error: bool = False
        self._memory: Decimal = _Q
        self._just_evaluated: bool = False

        self._publish()

    # ---- public surface ----

    def press(self, key: CalcKey) -> None:
        """Apply one key; updates the sink."""
        if self._error and key not in (CalcKey.CLEAR, CalcKey.CLEAR_ENTRY):
            return  # frozen until cleared
        if key in DIGITS:
            self._press_digit(key)
        elif key is CalcKey.DECIMAL:
            self._press_decimal()
        elif key in BINARY_OPS:
            self._press_binary(key)
        elif key is CalcKey.EQUALS:
            self._press_equals()
        elif key is CalcKey.CLEAR:
            self._clear(all_state=True)
        elif key is CalcKey.CLEAR_ENTRY:
            self._clear(all_state=False)
        elif key is CalcKey.BACKSPACE:
            self._backspace()
        elif key is CalcKey.NEGATE:
            self._negate()
        elif key is CalcKey.PERCENT:
            self._percent()
        elif key is CalcKey.SQRT:
            self._sqrt()
        elif key is CalcKey.SQUARE:
            self._square()
        elif key is CalcKey.INVERT:
            self._invert()
        elif key in (CalcKey.MEMORY_CLEAR, CalcKey.MEMORY_RECALL,
                     CalcKey.MEMORY_ADD, CalcKey.MEMORY_SUBTRACT,
                     CalcKey.MEMORY_STORE):
            self._press_memory(key)
        else:  # unknown — ignore
            return
        self._publish()

    def snapshot(self) -> dict[str, object]:
        """Return a JSON-serializable view of current state (for the API)."""
        return {
            "display": self._display,
            "expression": self._expression_tokens(),
            "error": self._error,
            "memory": _fmt(self._memory) if self._memory != _Q else "",
            "history": [{"expression": e, "result": r} for e, r in self._history.items],
        }

    # ---- digit / entry building ----

    def _press_digit(self, key: CalcKey) -> None:
        d = key.value
        if self._entering:
            self._display = d
            self._entering = False
        else:
            if self._display.replace("-", "").replace(".", "").__len__() >= _MAX_DIGITS:
                return
            if self._display == "0":
                self._display = d
            elif self._display == "-0":
                self._display = "-" + d
            else:
                self._display += d
        self._just_evaluated = False

    def _press_decimal(self) -> None:
        if self._entering:
            self._display = "0."
            self._entering = False
        elif "." not in self._display:
            self._display += "."
        self._just_evaluated = False

    # ---- binary operators ----

    def _press_binary(self, op: CalcKey) -> None:
        current = self._coerce_display()
        if self._pending_op is not None and not self._entering and not self._just_evaluated:
            # chained: evaluate the pending op first
            self._evaluate(current, freeze=False)
        else:
            self._accumulator = current
        self._pending_op = op
        self._entering = True
        self._just_evaluated = False

    def _press_equals(self) -> None:
        if self._pending_op is None:
            self._just_evaluated = True
            return
        current = self._coerce_display()
        expr = f"{_fmt(self._accumulator)} {self._pending_op.value} {_fmt(current)}"
        self._evaluate(current, freeze=True)
        self._history.add(expr, self._display)
        self._sink.add_history(expr, self._display)
        self._pending_op = None
        self._entering = True
        self._just_evaluated = True

    def _evaluate(self, right: Decimal, *, freeze: bool) -> None:
        """Apply the pending op with ``right``; on error, set error state."""
        try:
            result = self._apply(self._pending_op, self._accumulator, right)
        except (DivisionByZero, InvalidOperation):
            self._set_error()
            return
        self._accumulator = result
        self._display = _fmt(result)
        if freeze:
            pass  # display already set
        self._entering = True

    @staticmethod
    def _apply(op: CalcKey | None, left: Decimal, right: Decimal) -> Decimal:
        if op is CalcKey.ADD:
            return left + right
        if op is CalcKey.SUBTRACT:
            return left - right
        if op is CalcKey.MULTIPLY:
            return left * right
        if op is CalcKey.DIVIDE:
            if right == _Q:
                raise DivisionByZero
            return left / right
        return right  # no pending op

    # ---- unary helpers ----

    def _backspace(self) -> None:
        if self._entering:
            return  # nothing entered yet
        s = self._display
        if s in ("0", "-0", "0."):
            self._display = "0"
            self._entering = True
            return
        s = s[:-1]
        if s in ("", "-"):
            s = "0" if not s else "-0"
        # avoid trailing lone decimal point
        if s.endswith("."):
            s = s[:-1]
        self._display = s

    def _negate(self) -> None:
        if self._display == "0" or self._display == "0.":
            return
        self._display = self._display[1:] if self._display.startswith("-") else "-" + self._display

    def _percent(self) -> None:
        # standard calc: percent of the accumulator
        base = self._accumulator if self._pending_op is not None else self._coerce_display()
        current = self._coerce_display()
        result = (base * current) / Decimal(100)
        self._display = _fmt(result)
        self._entering = True

    def _sqrt(self) -> None:
        current = self._coerce_display()
        if current < 0:
            self._set_error()
            return
        result = current.sqrt()
        self._display = _fmt(result)
        self._entering = True
        self._just_evaluated = False

    def _square(self) -> None:
        current = self._coerce_display()
        self._display = _fmt(current * current)
        self._entering = True
        self._just_evaluated = False

    def _invert(self) -> None:
        current = self._coerce_display()
        if current == _Q:
            self._set_error()
            return
        self._display = _fmt(Decimal(1) / current)
        self._entering = True
        self._just_evaluated = False

    # ---- memory ----

    def _press_memory(self, key: CalcKey) -> None:
        current = self._coerce_display()
        if key is CalcKey.MEMORY_CLEAR:
            self._memory = _Q
        elif key is CalcKey.MEMORY_RECALL:
            self._display = _fmt(self._memory)
        elif key is CalcKey.MEMORY_ADD:
            self._memory += current
        elif key is CalcKey.MEMORY_SUBTRACT:
            self._memory -= current
        elif key is CalcKey.MEMORY_STORE:
            self._memory = current
        # an entry has been consumed / replaced; next digit starts fresh
        self._entering = True

    # ---- clear / error ----

    def _clear(self, *, all_state: bool) -> None:
        self._display = "0"
        self._error = False
        self._entering = True
        if all_state:
            self._accumulator = _Q
            self._pending_op = None
            self._just_evaluated = False

    def _set_error(self) -> None:
        self._error = True
        self._display = "无法除以零" if self._display else "错误"

    # ---- helpers ----

    def _coerce_display(self) -> Decimal:
        try:
            return Decimal(self._display)
        except (InvalidOperation, ValueError):
            return _Q

    def _expression_tokens(self) -> tuple[str, ...]:
        """Preview the pending expression as ordered tokens."""
        if self._pending_op is None:
            return ()
        return (_fmt(self._accumulator), self._pending_op.value, self._display)

    def _publish(self) -> None:
        """Push the full current state through the sink."""
        self._sink.set_primary(self._display, is_error=self._error)
        self._sink.set_expression(self._expression_tokens())
        mem = () if self._memory == _Q else (_fmt(self._memory),)
        self._sink.set_memory(mem)
        self._sink.set_error(self._error)
