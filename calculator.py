# === CONTEXT START ===
# This code defines a simple calculator class with methods for addition,
# subtraction, multiplication, and division. The division method includes error
# handling for division by zero.
# === CONTEXT END ===

class SimpleCalculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        if b == 0:
            raise ValueError('Cannot divide by zero')
        return a / b

# Example usage:
# calculator = SimpleCalculator()
# print(calculator.add(5, 3))  # Output: 8
# print(calculator.subtract(5, 3))  # Output: 2
# print(calculator.multiply(5, 3))  # Output: 15
# print(calculator.divide(5, 3))  # Output: 1.6666...
