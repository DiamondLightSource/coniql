import timeit

import numpy as np


def measure_numpy_comparison(size: int, runs: int) -> float:
    x_nums = np.array([x for x in range(size)], dtype=np.float64)
    y_nums = np.array([x for x in range(size)], dtype=np.float64)
    t = timeit.timeit(lambda: np.array_equal(x_nums, y_nums), number=runs)
    return t / runs


if __name__ == "__main__":

    SIZE = 1000000
    RUNS = 100

    # Using sets
    x_set = set([x for x in range(SIZE)])

    x_nums = [x for x in range(SIZE)]

    def compare_to_set():
        assert set(x_nums) == x_set

    t1 = timeit.timeit(compare_to_set, number=RUNS)
    print(f"PYTHON - Size: {SIZE} took: {t1 / RUNS} seconds on average")

    x_np_array = np.array([x for x in range(SIZE)], dtype=np.float64)
    y_np_array = np.array([x for x in range(SIZE)], dtype=np.float64)

    t2 = timeit.timeit(lambda: np.array_equal(x_np_array, y_np_array), number=RUNS)
    print(f"NUMPY - Size: {SIZE} took: {t2 / RUNS} seconds on average")

    for x in range(10):
        size = x * 100000
        print(f"Size: {x}e5 - {measure_numpy_comparison(size, 1000)}")
