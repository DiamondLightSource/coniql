# Script to perform processing of the Kubernetes-based performance test
# and provide useful output
import json
import re
import statistics
import subprocess
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import requests

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

job_output = subprocess.run(
    ["kubectl", "get", "jobs", "kubernetes-performance-test", "-o", "json"],
    capture_output=True,
    text=True,
    check=True,
).stdout

job_json: Dict[str, Any] = json.loads(job_output)

start_time = datetime.strptime(job_json["status"]["startTime"], DATETIME_FORMAT)
completion_time = datetime.strptime(
    job_json["status"]["completionTime"], DATETIME_FORMAT
)

duration = completion_time - start_time

# Add some time as there's lag for the data to make it into Prometheus
data_offset_seconds = 30
# TODO: Work out a better data window - the data for the CPU is delayed more than the
# delay for the memory...
start_time_offset = start_time + timedelta(seconds=30)
completion_time_offset = completion_time + timedelta(seconds=data_offset_seconds)

print("Waiting for data to appear in Prometheus...")
time.sleep(data_offset_seconds)


prometheus_url = "https://argus-prometheus.diamond.ac.uk/api/v1/query_range"

# TODO: Namespace!
query = (
    "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate"
    "{namespace='eyh46967', container='coniql'}"
)

params = {
    # Trailing "Z" required to match Prometheus's requirement on datetime format
    "start": start_time_offset.isoformat() + "Z",
    "end": completion_time_offset.isoformat() + "Z",
    "query": query,
    "step": "15s",
}
r = requests.get(url=prometheus_url, params=params)
print(r.url)
r.raise_for_status()

data = r.json()

values = [float(x[1]) for x in data["data"]["result"][0]["values"]]

cpu_mean = statistics.mean(values)
cpu_max = max(values)
cpu_median = statistics.median(values)

# TODO: namespace
query = 'container_memory_working_set_bytes{namespace="eyh46967", container="coniql"}'
params["query"] = query

r = requests.get(url=prometheus_url, params=params)
print(r.url)
r.raise_for_status()

data = r.json()
values = [float(x[1]) for x in data["data"]["result"][0]["values"]]

mem_mean = statistics.mean(values)
mem_max = max(values)
mem_median = statistics.median(values)


logs_output = subprocess.run(
    [
        "kubectl",
        "logs",
        "-l",
        "job-name=kubernetes-performance-test",
        # Last 3 lines are "SUMMARY", average missed events, max missed events
        "--tail=3",
    ],
    capture_output=True,
    text=True,
    check=True,
).stdout

average_missed_events = re.findall("Average missed events = (\\d*)", logs_output)
average_missed_events = [int(x) for x in average_missed_events]

max_missed_events = re.findall("Max. missed events = (\\d*)", logs_output)
max_missed_events = [int(x) for x in max_missed_events]


MBFACTOR = float(1 << 20)  # 1048576 == bytes in a Mebibyte

print("Statistics:")
print("CPU Usage:")
print(f"  Mean:             {cpu_mean * 100:.2f}%")
print(f"  Max:              {cpu_max* 100:.2f}%")
print(f"  Median:           {cpu_median* 100:.2f}%")
print("Memory Usage:")
print(f"  Mean:             {mem_mean / MBFACTOR:.2f} MiB")
print(f"  Max:              {mem_max / MBFACTOR:.2f} MiB")
print(f"  Median:           {mem_median / MBFACTOR:.2f} MiB")
print("Job:")
print(f"  Start time:       {start_time}")
print(f"  End time:         {completion_time}")
print(f"  Duration:         {duration}")
print(f"Mean events missed: {statistics.mean(average_missed_events)}")
print(f"Max events missed:  {max(max_missed_events)}")


# Create Prometheus URL for graphs of CPU and Memory of Coniql container

time_from_start = duration + timedelta(seconds=data_offset_seconds)

# Add padding so we can clearly see start and end
range_input = time_from_start.seconds + 60
end_input = completion_time + timedelta(seconds=60)

graph_params = {
    "g0.expr": (
        'container_memory_working_set_bytes{namespace="eyh46967", container="coniql"}'
    ),
    "g0.tab": "0",
    "g0.stacked": "1",
    "g0.range_input": f"{range_input}s",
    "g0.end_input": f"{end_input.isoformat()}",
    "g1.expr": (
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate"
        '{namespace="eyh46967", container="coniql"}'
    ),
    "g1.tab": "0",
    "g1.stacked": "1",
    "g1.range_input": f"{range_input}s",
    "g1.end_input": f"{end_input.isoformat()}",
}
r = requests.get(
    url="https://argus-prometheus.diamond.ac.uk/graph", params=graph_params
)
print(r.url)
