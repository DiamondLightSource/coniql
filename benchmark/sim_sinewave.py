"""Measure the performance of sine waves of various sizes"""
import base64
import numpy as np

from typing import List

from measure import measure_request_times, print_request_times


def to_float_array(input_data: str) -> List[float]:
    buffer = base64.decodebytes(input_data.encode("ascii"))
    return np.frombuffer(buffer, dtype=np.float64)


def measure_and_print_simple_sinewave(size: int, repeats: int = 100):
    def validate_from_json(data: dict) -> bool:
        encoded_numbers = data["data"]["getChannel"]["value"]["base64"]
        number_array = to_float_array(encoded_numbers)
        return set(number_array) == set([x for x in range(size)])

    print_request_times(
        measure_request_times(request, validate=validate_from_json),
        f"Sine Wave of size {size}",
    )


if __name__ == "__main__":
    measure_and_print_simple_sinewave(1)
    measure_and_print_simple_sinewave(10)
    measure_and_print_simple_sinewave(100)
    measure_and_print_simple_sinewave(1000)
    measure_and_print_simple_sinewave(10000)
    measure_and_print_simple_sinewave(100000)
    measure_and_print_simple_sinewave(1000000)
    measure_and_print_simple_sinewave(10000000)
