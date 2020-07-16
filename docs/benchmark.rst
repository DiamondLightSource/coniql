Benchmarking
============

In order to evaluate changes made to the server, we have developed some scripts which request increasingly large waveforms and measure the update rate.
Benchmark scripts are written in both Python and js (using the Node runtime) in an attempt to remove language or runtime effects.
It is possible other graphQL clients will provide different performance characteristics in the future, although we have good reason to believe we are currently hitting other limits.
For more information on the results of benchmarking so far, see `this page.<https://github.com/dls-controls/cs-web-proto/wiki/Performance-with-the-Backend>`_.

Instructions
------------

Python Client
~~~~~~~~~~~~~

To setup the Python client, install the development dependencies::

    pipenv install --dev

Open a terminal and run the server::

    pipenv run python -m coniql

Open a new terminal and run the client::

    pipenv run python benchmark/asyncClient.py

JS Client
~~~~~~~~~

To run the JS client, you must first install Node.js on your system.
Follow the instructions `here.<https://nodejs.org/en/>`_.

Then, install the necessary (and minimal) JS packages::

    npm install

Open a terminal and run the server::

    pipenv run python -m coniql

Open a new terminal and run the client::

    node benchmark/jsThroughputTest.py