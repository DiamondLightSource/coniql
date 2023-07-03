#!/bin/bash
# Run the Performance test in Kubernetes. 

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CONIQL_YAML=$SCRIPT_DIR/coniql.yaml
JOB_YAML=$SCRIPT_DIR/job.yaml


build() 
{
    # Build the ioc container
    podman build --tag=gcr.io/diamond-privreg/controls/coniql/ioc:latest --target=ioc .

    # Build the Python client
    podman build --tag=gcr.io/diamond-privreg/controls/coniql/perf_client:latest --target=perf_client .

    # Publish them to Google Container Registry
    podman push gcr.io/diamond-privreg/controls/coniql/ioc:latest
    podman push gcr.io/diamond-privreg/controls/coniql/perf_client
}

#   - TODO: Perhaps also get a final read from Coniql's /metrics endpoint?

start_coniql() 
{
  kubectl apply -f $CONIQL_YAML
  # Give moment for Kubernetes to create Pod
  sleep 1
  kubectl wait --timeout=-1s --for=condition=ready pod -l app=coniql
}

start_job() 
{
  kubectl apply -f $JOB_YAML

  # Wait for completion in background - will return 0 if occurs
  kubectl wait --timeout=-1s --for=condition=complete job/kubernetes-performance-test &
  completion_pid=$!

  # Wait for failure in background - will return 1 if occurs
  kubectl wait --timeout=-1s --for=condition=failed job/kubernetes-performance-test && exit 1 &
  failed_pid=$!

  # Capture exit code of the first subprocess to exit
  wait -n $completion_pid $failed_pid
  exit_code=$?

  if (( $exit_code == 0 )); then
    echo "Job completed"
  else
    echo "Job failed"
  fi

  return $exit_code

}

stop_coniql()
{
  kubectl delete -f $CONIQL_YAML
  kubectl wait --timeout=-1s --for=delete pod -l app=coniql
}

stop_job()
{
  kubectl delete -f $JOB_YAML
  kubectl wait --timeout=-1s --for=delete job/kubernetes-performance-test
}


start_coniql
start_job
result=$?

stop_coniql

if (( $result == 0 )); then
    python $SCRIPT_DIR/process_results.py
    stop_job
  else
    echo "Leaving Job for investigation"
  fi





