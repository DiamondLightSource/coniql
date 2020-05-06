coniql
===========================

|build_status| |coverage| |pypi_version| |readthedocs|

Control system interface in GraphQL with plugins for EPICS Channel Access and PV Access.
Supports a web interface to get, put and monitor the value of PVs.

Documentation
-------------

Full documentation is available at http://coniql.readthedocs.io

Source Code
-----------

Available from http://github.com/dls-controls/coniql

Installation
------------

Install the dependencies using instructions from:

https://confluence.diamond.ac.uk/display/SSCC/Python+3+User+Documentation

Then you can run the example::
    
    pipenv run python -m coniql.server

And see the graphiql interface here:

http://localhost:8000/graphiql

With something like::

    subscription {
      subscribeChannel(id: "sim://sine") {
        id
        meta {
          __typename
          description
          tags
          label
          ... on ObjectMeta {
            array
            type
          }
          ... on NumberMeta {
            array
            numberType
            display {
              controlRange {
                min
                max
              }
              displayRange {
                min
                max
              }
              alarmRange {
                min
                max
              }
              warningRange {
                min
                max
              }
              units
              precision
              form
            }
          }
          ... on EnumMeta {
            array
            choices
          }
        }
        value
        time {
          seconds
          nanoseconds
          userTag
        }
        status {
          quality
          message
          mutable
        }
      }
    }


Sim Plugin
----------

The sim plugin provides a number of channels that accept keyword args. For a
channel `channel` which takes up to 3 args, the allowed combinations are::

    sim://channel
    sim://channel(arg1)
    sim://channel(arg1, arg2)
    sim://channel(arg1, arg2, arg3)

Any unspecified arguments are defaulted.

Available channels:

- sim://sine(min_value, max_value, steps, update_seconds, warning_percent, alarm_percent)
- sim://sinewave(period_seconds, sample_wavelength, size, update_seconds, min_value, max_value, warning_percent, alarm_percent)

PVA Plugin
----------

Coniql will provide its values over pvAccess.
This requires a working installation of `<EPICS 7 https://epics.anl.gov/base/R7-0/index.php>`_.

Then set the environment variable **EPICS7_BASE** to the top level of the installation::

    export EPICS7_BASE=/path/to/EPICS

This should allow the values within the coniql database to be made available over pvAccess.

Measuring Performance
---------------------

If you have followed the above instructions and conqil is running at *localhost:8000*, then performance tests can be run with:

.. code-block:: bash

  pipenv run python benchmark/sim_sine.py 
To start using this template::

    git clone https://github.com/dls-controls/coniql

Contributing
------------

See `CONTRIBUTING`_

License
-------
APACHE License. (see `LICENSE`_)


.. |build_status| image:: https://travis-ci.com/dls-controls/coniql.svg?branch=master
    :target: https://travis-ci.com/dls-controls/coniql
    :alt: Build Status

.. |coverage| image:: https://coveralls.io/repos/github/dls-controls/coniql/badge.svg?branch=master
    :target: https://coveralls.io/github/dls-controls/coniql?branch=master
    :alt: Test Coverage

.. |pypi_version| image:: https://badge.fury.io/py/coniql.svg
    :target: https://badge.fury.io/py/coniql
    :alt: Latest PyPI version

.. |readthedocs| image:: https://readthedocs.org/projects/coniql/badge/?version=latest
    :target: http://coniql.readthedocs.io
    :alt: Documentation

.. _CONTRIBUTING:
    https://github.com/dls-controls/coniql/blob/master/CONTRIBUTING.rst

.. _LICENSE:
    https://github.com/dls-controls/coniql/blob/master/LICENSE
