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

# Add 2 minutes as there's lag for the data to make it into Prometheus
data_offset_seconds = 120
start_time = start_time + timedelta(seconds=data_offset_seconds)
completion_time = completion_time + timedelta(seconds=data_offset_seconds)

duration = duration + timedelta(seconds=data_offset_seconds)

# Add 2 mins to completion time to account for lag in the data appearing in Prometheus
print("Waiting for data to appear in Prometheus...")
time.sleep(data_offset_seconds)


prometheus_url = "https://pollux-prometheus.diamond.ac.uk/api/v1/query_range"

# TODO: Namespace!
query = (
    "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate"
    "{namespace='eyh46967', container='coniql'}"
)

params = {
    "start": start_time.isoformat() + "Z",
    "end": completion_time.isoformat() + "Z",
    "query": query,
    "step": "15s",
}
r = requests.get(url=prometheus_url, params=params)
print(r.url)

r.raise_for_status()

data = r.json()

values = [float(x[1]) for x in data["data"]["result"][0]["values"]]

mean = statistics.mean(values)
max_val = max(values)
median = statistics.median(values)

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

print("Statistics:")
print("CPU Usage:")
print(f"  Mean:             {mean}")
print(f"  Max:              {max_val}")
print(f"  Median:           {median}")
print(f"Job duration:       {duration}")
print(f"Mean events missed: {statistics.mean(average_missed_events)}")
print(f"Max events missed:  {max(max_missed_events)}")
