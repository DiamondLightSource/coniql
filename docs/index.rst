coniql
======

Control system interface in GraphQL

Installation
------------

Install the dependencies using instructions from:

https://confluence.diamond.ac.uk/display/SSCC/Python+3+User+Documentation

Then you can run the example::

    pipenv run python -m coniql

And see the graphiql interface here:

http://localhost:8080/graphiql

With something like::

    subscription{
      subscribeChannel(id: "sim://sine") {
        id
        value {
          float
        }
        time {
          datetime
        }
        status {
          quality
          message
          mutable
        }
        display {
          label
          description
          role
          widget
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
          choices
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
