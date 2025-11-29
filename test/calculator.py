# === CONTEXT START ===
# This module defines a reusable Calculator class with basic arithmetic operations.
# === CONTEXT END ===

class Calculator:
    """
    A simple calculator class to perform basic arithmetic operations.
    """

    def add(self, a: float, b: float) -> float:
        """
        Returns the sum of a and b.

        :param a: First number to add.
        :param b: Second number to add.
        :return: The sum of a and b.
        """
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """
        Returns the difference of a and b.

        :param a: Number to subtract from.
        :param b: Number to subtract.
        :return: The difference of a and b.
        """
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """
        Returns the product of a and b.

        :param a: First number to multiply.
        :param b: Second number to multiply.
        :return: The product of a and b.
        """
        return a * b

    def divide(self, a: float, b: float) -> float:
        """
        Returns the quotient of a and b. Raises a ValueError if b is zero.

        :param a: Numerator.
        :param b: Denominator.
        :return: The quotient of a and b.
        :raises ValueError: If b is zero.
        """
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b
