"""Tests for the pure standard calculator engine.

A fake :class:`DisplaySink` records every callback so the engine is
verified without any framework. These mirror the behaviors of Windows
Calculator standard mode: chained operators, equals+history, unary ops,
memory, and error freeze.
"""

from __future__ import annotations

from decimal import Decimal

from platform_runtime.domain.calculator import CalcKey, CalculatorEngine


class FakeSink:
    def __init__(self) -> None:
        self.primary = "0"
        self.is_error = False
        self.tokens: tuple[str, ...] = ()
        self.memory: tuple[str, ...] = ()
        self.history: list[tuple[str, str]] = []

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


def _engine() -> tuple[CalculatorEngine, FakeSink]:
    sink = FakeSink()
    return CalculatorEngine(sink), sink


def _press(engine: CalculatorEngine, keys: list[CalcKey]) -> None:
    for k in keys:
        engine.press(k)


def test_initial_state_is_zero_and_published() -> None:
    engine, sink = _engine()
    assert sink.primary == "0"
    assert sink.is_error is False
    assert sink.tokens == ()
    assert sink.memory == ()


def test_digit_entry_replace_then_append() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.ONE, CalcKey.TWO, CalcKey.THREE])
    assert sink.primary == "123"


def test_leading_zero_collapses() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.ZERO, CalcKey.ZERO, CalcKey.FIVE])
    assert sink.primary == "5"


def test_decimal_point_single() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.ONE, CalcKey.DECIMAL, CalcKey.TWO, CalcKey.DECIMAL, CalcKey.THREE])
    assert sink.primary == "1.23"


def test_addition_evaluates_and_records_history() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.TWO, CalcKey.ADD, CalcKey.THREE, CalcKey.EQUALS])
    assert sink.primary == "5"
    assert sink.history == [("2 + 3", "5")]


def test_chained_operators_evaluate_left_to_right() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.TWO, CalcKey.ADD, CalcKey.THREE, CalcKey.MULTIPLY, CalcKey.FOUR, CalcKey.EQUALS])
    # (2+3)=5 then *4 = 20
    assert sink.primary == "20"
    assert sink.history[-1] == ("5 * 4", "20")


def test_clear_all_resets_state_keeps_memory() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.FIVE, CalcKey.MEMORY_STORE, CalcKey.ADD, CalcKey.THREE, CalcKey.CLEAR])
    assert sink.primary == "0"
    assert sink.memory == ("5",)


def test_clear_entry_clears_only_entry() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.TWO, CalcKey.ADD, CalcKey.THREE, CalcKey.CLEAR_ENTRY])
    assert sink.primary == "0"
    # pending op preserved: 3 + ? still has accumulator 2
    assert sink.tokens[:2] == ("2", "+")


def test_negate_flips_sign() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.FIVE, CalcKey.NEGATE])
    assert sink.primary == "-5"
    engine.press(CalcKey.NEGATE)
    assert sink.primary == "5"


def test_percent_of_accumulator() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.ONE, CalcKey.ZERO, CalcKey.ZERO, CalcKey.ADD, CalcKey.ONE, CalcKey.ZERO, CalcKey.PERCENT])
    # 10% of 100 = 10
    assert sink.primary == "10"


def test_sqrt_of_nine() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.NINE, CalcKey.SQRT])
    # sqrt(9) = 3
    assert Decimal(sink.primary) == Decimal(3)


def test_invert_of_four() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.FOUR, CalcKey.INVERT])
    assert Decimal(sink.primary) == Decimal("0.25")


def test_division_by_zero_sets_error_and_freezes() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.FIVE, CalcKey.DIVIDE, CalcKey.ZERO, CalcKey.EQUALS])
    assert sink.is_error is True
    # frozen: further digits ignored
    engine.press(CalcKey.SEVEN)
    assert sink.is_error is True
    # clear unfreezes
    engine.press(CalcKey.CLEAR)
    assert sink.is_error is False
    assert sink.primary == "0"


def test_memory_add_recall() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.FIVE, CalcKey.MEMORY_ADD, CalcKey.THREE, CalcKey.MEMORY_ADD])
    assert sink.memory == ("8",)
    _press(engine, [CalcKey.CLEAR, CalcKey.MEMORY_RECALL])
    assert sink.primary == "8"


def test_snapshot_is_json_serializable() -> None:
    engine, _ = _engine()
    _press(engine, [CalcKey.TWO, CalcKey.ADD, CalcKey.THREE, CalcKey.EQUALS])
    snap = engine.snapshot()
    assert snap["display"] == "5"
    assert snap["error"] is False
    assert isinstance(snap["history"], list)
    assert snap["history"][-1] == {"expression": "2 + 3", "result": "5"}


def test_engine_satisfies_display_sink_protocol() -> None:
    from platform_runtime.domain.ports import DisplaySink
    sink = FakeSink()
    # FakeSink has the DisplaySink shape; engine accepts it
    assert isinstance(sink, DisplaySink)


def test_backspace_deletes_last_digit() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.ONE, CalcKey.TWO, CalcKey.THREE, CalcKey.BACKSPACE])
    assert sink.primary == "12"


def test_backspace_to_zero() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.FIVE, CalcKey.BACKSPACE])
    assert sink.primary == "0"
    # subsequent digits start fresh
    engine.press(CalcKey.SEVEN)
    assert sink.primary == "7"


def test_backspace_after_decimal_strips_trailing_dot() -> None:
    engine, sink = _engine()
    _press(engine, [CalcKey.ONE, CalcKey.DECIMAL, CalcKey.TWO, CalcKey.BACKSPACE])
    assert sink.primary == "1"
