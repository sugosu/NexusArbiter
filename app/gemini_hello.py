def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

print('Hello from Gemini 2.0!')

n = 10
fib_number = fibonacci(n)
print(f'The {n}th Fibonacci number is: {fib_number}')