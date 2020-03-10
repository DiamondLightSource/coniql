from statistics import mean, median
import time
from typing import List, Optional

import requests


def measure_request_times(
    query: str,
    repeats: int = 100,
    url: str = "http://localhost:8000/graphql",
    validate: Optional[callable] = None,
):
    request_times = []
    for request_num in range(repeats):
        start_time = time.time()
        result = requests.post(url, json={"query": query})
        assert result.status_code == 200
        end_time = time.time()

        # Validate the data if provided
        if validate:
            assert validate(result.json())

        # Store time in ms
        request_times.append((end_time - start_time) * 1000)
    return request_times


def print_request_times(request_times: List[float], label: Optional[str] = None):
    if label:
        print(f"----- {label} -----")
    else:
        print("---------------")
    print(f"Measured {len(request_times)} times:")
    print(f"Shortest time:\t{min(request_times):4f} ms")
    print(f"Longest time:\t{max(request_times):4f} ms")
    print(f"Mean time:\t{mean(request_times):4f} ms")
    print(f"Median time:\t{mean(request_times):4f} ms")
