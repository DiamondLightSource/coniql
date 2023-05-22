Benchmarking
============

In order to evaluate changes made to the server, we have developed some scripts which request increasingly large waveforms and measure the update rate.
Benchmark scripts are written in both Python and js (using the Node runtime) in an attempt to remove language or runtime effects.
It is possible other graphQL clients will provide different performance characteristics in the future, although we have good reason to believe we are currently hitting other limits.
For more information on the results of benchmarking so far, see `this page <https://github.com/DiamondLightSource/cs-web-proto/wiki/Performance-with-Coniql>`_.

Instructions
------------

Python Client
~~~~~~~~~~~~~

To setup the Python client, install the development dependencies::

    pip install -e .[dev]

Open a terminal and run the server::

    python -m coniql

Open a new terminal and run the client::

    python benchmark/asyncClient.py

JS Client
~~~~~~~~~

To run the JS client, you must first install Node.js on your system.
Follow the instructions `here <https://nodejs.org/en/>`_.

Then, install the necessary (and minimal) JS packages::

    npm install

Open a terminal and run the server::

    python -m coniql

Open a new terminal and run the client::

    node benchmark/jsThroughputTest.py

Expected Results
~~~~~~~~~~~~~~~~

Both clients are requesting increasingly large waveforms with an update time of 0.1s.
Therefore, the frequency printed after each test should be around 10 Hz to start with.
Naturally this will drop off as the size increases.

Once all of the tests have run, a final summary will be printed to the terminal which can be easily copied and pasted into your desired spreadsheet software.