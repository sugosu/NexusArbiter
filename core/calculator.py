# === CONTEXT START ===
# Added logging to the Calculator class to log each operation and its result.
# Configured logging in the constructor and added debug logs for each arithmetic
# operation. An error log is added for division by zero.
# === CONTEXT END ===

# === CONTEXT START ===
# This file contains a basic calculator class that can perform addition,
# subtraction, multiplication, and division.
# === CONTEXT END ===

import logging

class Calculator:
    """
    A basic calculator class that can perform simple arithmetic operations.
    """

    def __init__(self):
        # Configure logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def add(self, a, b):
        """Return the sum of a and b."""
        result = a + b
        self.logger.debug(f"Adding {a} + {b} = {result}")
        return result

    def subtract(self, a, b):
        """Return the difference of a and b."""
        result = a - b
        self.logger.debug(f"Subtracting {a} - {b} = {result}")
        return result

    def multiply(self, a, b):
        """Return the product of a and b."""
        result = a * b
        self.logger.debug(f"Multiplying {a} * {b} = {result}")
        return result

    def divide(self, a, b):
        """Return the quotient of a and b. Raises ValueError if b is zero."""
        if b == 0:
            self.logger.error("Attempted to divide by zero.")
            raise ValueError("Cannot divide by zero.")
        result = a / b
        self.logger.debug(f"Dividing {a} / {b} = {result}")
        return result
