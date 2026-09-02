"""Calculator keys — the input alphabet of the standard engine.

Borrowed from Microsoft Calculator's ``NumbersAndOperatorsEnum``: a single
enum names every input the engine accepts, so the engine, the API, and the
frontend share one vocabulary. Standard mode only; scientific/programmer
modes extend this in their own modules.
"""

from __future__ import annotations

from enum import StrEnum


class CalcKey(StrEnum):
    # Digits
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    DECIMAL = "."

    # Binary operators
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"

    # Evaluate / clear
    EQUALS = "="
    CLEAR = "C"          # clear all (memory kept)
    CLEAR_ENTRY = "CE"   # clear current entry only
    BACKSPACE = "back"   # delete last digit of current entry

    # Unary / helper
    NEGATE = "+/-"        # flip sign of current entry
    PERCENT = "%"         # percent of accumulator (standard behavior)
    SQRT = "sqrt"         # square root of current entry
    SQUARE = "x²"         # square of current entry
    INVERT = "1/x"        # reciprocal of current entry

    # Memory (standard MC/MR/M+/M-/MS)
    MEMORY_CLEAR = "MC"
    MEMORY_RECALL = "MR"
    MEMORY_ADD = "M+"
    MEMORY_SUBTRACT = "M-"
    MEMORY_STORE = "MS"


BINARY_OPS: frozenset[CalcKey] = frozenset(
    {CalcKey.ADD, CalcKey.SUBTRACT, CalcKey.MULTIPLY, CalcKey.DIVIDE}
)
DIGITS: frozenset[CalcKey] = frozenset(
    {CalcKey.ZERO, CalcKey.ONE, CalcKey.TWO, CalcKey.THREE, CalcKey.FOUR,
     CalcKey.FIVE, CalcKey.SIX, CalcKey.SEVEN, CalcKey.EIGHT, CalcKey.NINE}
)
MEMORY_OPS: frozenset[CalcKey] = frozenset(
    {CalcKey.MEMORY_CLEAR, CalcKey.MEMORY_RECALL, CalcKey.MEMORY_ADD,
     CalcKey.MEMORY_SUBTRACT, CalcKey.MEMORY_STORE}
)
