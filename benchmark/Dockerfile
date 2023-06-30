# This file contains the images for the performance test


# perf_client contains the Python client code that connects to the Coniql 
# server via websockets
FROM python:3.10 as perf_client

# set up a virtual environment and put it in PATH
RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH

RUN pip install websockets

# The Python client script
COPY ./coniql_performance_test.py .

ENTRYPOINT [ "python", "./coniql_performance_test.py" ]

CMD [ \
      "-n", "100", \
      "-s", "1000",  \
      "-p", "2", \
      "-f", "results.txt", \
      "--kubernetes", \
]

# ioc generates a configurable sized DB, then runs an IOC 
FROM ghcr.io/epics-containers/epics-base-linux-runtime:23.6.1 as ioc

COPY ./generate_db.sh .
COPY ./build_and_run_ioc.sh .

ENTRYPOINT [ "./build_and_run_ioc.sh" ]
CMD [ "100" ]