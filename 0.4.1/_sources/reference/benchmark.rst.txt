Benchmarking
============

In order to evaluate how changes made to the server impact the performance we have created a benchmarking script to measure the CPU usage, memory usage
and the number of dropped updates. This script is written in Python. The script creates a websocket client and starts subscriptions to a configurable
number of EPICS PVs. A separate thread measures the CPU and memory usage of the Coniql application while the subscriptions are running. After _N_ samples
have been collected the thread will finish and the average CPU and memory usage will be saved to file and printed to screen. The results of the subscriptions
are also analysed to determine how many updates were missed by Coniql.

These tests require an EPICS IOC running a specific _.db_ file with _N_ PVs counting up at a rate of 10 Hz. An instance of Coniql must also be running.

To facilitate the running of all these components a bash script has also been provided. This will handle the creation of the .db file, starting the
EPICS IOC, starting Coniql, and running the Python performance tests.


Instructions
------------

Prerequisites
~~~~~~~~~~~~~

- EPICS installed
- Coniql installed in a Python virtual environment

Bash script
~~~~~~~~~~~~~

To run the bash script::

    ./benchmark/run_performance_test.sh --path <path/to/coniql/venv>

The path to the Python virtual enviroment where Coniql is installed is required.

By default this will run the Python performance tests with the following configuration:

- 1 client
- subscriptions to 100 PVs
- collect 1000 samples
- use the new websocket protocol (graphql-transport-ws)

These parameters can be configured using the following script options:

- ``-c <n>`` number of clients to start
- ``-n <n>`` number of PVs to subscribe to
- ``-s <n>`` number of samples to collect
- ``-w <1/2>`` websocket protocol to use (1=graphql-ws, 2=graphql-transport-ws)

See script ``--help`` option for more details.


Expected Results
~~~~~~~~~~~~~~~~

Results will be output to ``benchmark/performance_test_results_NClients_X.txt``.

Logs from the EPICS IOC, Coniql and Python performance script will be saved in ``benchmark/logs/``.

The results of the performance test should be compared between updates to the code. For the same number of clients, PVs, samples, and the same
websocket protocol check that the CPU, memory and number of dropped updates remains consistent with previous results.
