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
    podman push gcr.io/diamond-privreg/controls/coniql/ioc
    podman push gcr.io/diamond-privreg/controls/coniql/perf_client
}

#   - TODO: Perhaps also get a final read from Coniql's /metrics endpoint?

install_chart()
{
  NUM_CLIENTS=$1
  helm install myperftest $SCRIPT_DIR/perf_test \
    --set perf_client.completions=$NUM_CLIENTS \
    --set perf_client.parallelism=$NUM_CLIENTS
}

uninstall_chart()
{
  helm uninstall myperftest 
  # The Coniql pod is the slowest thing to terminate, so wait for it to disappear
  kubectl wait --timeout=-1s --for delete pod -l app=coniql
}


wait_for_job_ending()
{
  echo "Waiting for Job to complete"

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

# Number of Python client programs to run in parallel
# CLIENTS=(1 2 5 10 20 50)

CLIENTS=(50)




for NUM_CLIENTS in ${CLIENTS[@]}; do
  echo "Beginning test. Clients: $NUM_CLIENTS"
  install_chart $NUM_CLIENTS

  wait_for_job_ending
  result=$?

  if (( $result == 0 )); then
      python $SCRIPT_DIR/process_results.py
      uninstall_chart
  else
      echo "Leaving Chart for investigation"
      exit
  fi
done