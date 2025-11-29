# === CONTEXT START ===
# This module implements a simple calculator with basic arithmetic operations.
# It includes methods for addition, subtraction, multiplication, and division.
# The division method handles division by zero by raising a ValueError.
# === CONTEXT END ===

class Calculator:
    """A simple calculator class to perform basic arithmetic operations."""

    def add(self, a: float, b: float) -> float:
        """Return the sum of a and b."""
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """Return the difference of a and b."""
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """Return the product of a and b."""
        return a * b

    def divide(self, a: float, b: float) -> float:
        """Return the division of a by b. Raise ValueError if b is zero."""
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b
