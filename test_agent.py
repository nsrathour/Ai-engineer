"""Simple example logic to add, multiply, and divide two numbers.

Run:
    python test_agent.py
"""

from __future__ import annotations


def add_two_numbers(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b


def multiply_two_numbers(a: float, b: float) -> float:
    """Return the product of two numbers."""
    return a * b


def divide_two_numbers(a: float, b: float) -> float:
    """Return a / b.

    Raises:
        ZeroDivisionError: if b == 0
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


def _run_tests() -> None:
    # ---- Addition tests ----
    assert add_two_numbers(1, 2) == 3
    assert add_two_numbers(0, 0) == 0
    assert add_two_numbers(-1, 1) == 0
    assert add_two_numbers(2.5, 4.1) == 6.6

    # ---- Multiplication tests ----
    assert multiply_two_numbers(2, 3) == 6
    assert multiply_two_numbers(0, 10) == 0
    assert multiply_two_numbers(-2, 4) == -8
    assert multiply_two_numbers(2.5, 4.0) == 10.0

    # ---- Division tests ----
    assert divide_two_numbers(6, 3) == 2
    assert divide_two_numbers(1, 4) == 0.25
    assert divide_two_numbers(-9, 3) == -3

    # Division by zero should raise
    try:
        divide_two_numbers(1, 0)
        raise AssertionError("Expected ZeroDivisionError")
    except ZeroDivisionError:
        pass


if __name__ == "__main__":
    _run_tests()
    print("All tests passed.")
