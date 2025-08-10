"""Basic benchmark tests to ensure CI runs properly."""

import time


def simple_function(n: int) -> int:
    """Simple function for benchmarking."""
    total = 0
    for i in range(n):
        total += i
    return total


def test_simple_benchmark(benchmark):
    """Basic benchmark test."""
    result = benchmark(simple_function, 1000)
    assert result == sum(range(1000))


def test_performance_baseline(benchmark):
    """Performance baseline test."""

    def sleep_function():
        time.sleep(0.001)
        return True

    result = benchmark(sleep_function)
    assert result is True
