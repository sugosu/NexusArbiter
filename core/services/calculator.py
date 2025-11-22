# === CONTEXT START ===
# This class provides basic arithmetic operations such as addition, subtraction,
# multiplication, and division.
# === CONTEXT END ===

class Calculator:
    """
    CONTEXT: This class provides basic arithmetic operations such as addition, subtraction, multiplication, and division.
    """

    def add(self, a, b):
        """Return the sum of a and b."""
        return a + b

    def subtract(self, a, b):
        """Return the difference of a and b."""
        return a - b

    def multiply(self, a, b):
        """Return the product of a and b."""
        return a * b

    def divide(self, a, b):
        """Return the quotient of a and b. Raises ValueError if b is zero."""
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b
