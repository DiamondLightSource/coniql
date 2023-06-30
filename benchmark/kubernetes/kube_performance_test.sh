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
  kubectl wait --timeout=-1s --for=condition=complete job/kubernetes-performance-test
}

stop_coniql()
{
  kubectl delete -f $CONIQL_YAML
  kubectl wait --timeout=-1s --for=delete pod -l app=coniql
}

stop_job()
{
  kubectl delete -f $JOB_YAML
  kubectl wait --timeout=-1s --for=delete pod -l app=coniql
}


start_coniql
start_job

stop_coniql

python $SCRIPT_DIR/process_results.py

stop_job


