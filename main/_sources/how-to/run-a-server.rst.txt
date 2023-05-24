Run a server
============

Coniql exposes an interface to Channels. A Channel maps to a single
value, with timeStamp, status information, and display level metadata. 
Channels can be backed by different data stores, provided via a plugin 
interface.

For example:

.. image:: ../images/concrete-device-layer.svg

Running a server
----------------

You can run up a simulation server like this::

  pipenv run python -m coniql

Then you can test the connection with the graphiql interface:

http://localhost:8080/graphiql

You can type in queries, pressing Ctrl + space to autocomplete. Below are some examples to try.

Getting a channel
~~~~~~~~~~~~~~~~~

A query like the following::

  query {
    getChannel(id: "ssim://sine") {
      value {
        float
      }
      time {
        datetime
      }
    }
  }

Will ask for the current value of the given Channel, selecting the value as a
float, and the time as a datetime. It returns::

  {
    "data": {
      "getChannel": {
        "value": {
          "float": -4.755282581475768
        },
        "time": {
          "datetime": "2020-06-12T13:10:39.875753"
        }
      }
    }
  }

The first part of the id is the protocol to get the Channel from, and the
second part is the channel name. See the sections on plugins below for
details.

Subscribing to a Channel
~~~~~~~~~~~~~~~~~~~~~~~~

To get updates whenever a Channel changes, you can use subscribeChannel. This returns
Channel objects with non-changing top level fields set to null. For example, if we
ask for the value, status and display of the same Channel::

  subscription {
    subscribeChannel(id: "ssim://sine") {
      value {
        string
      }
      status {
        quality
      }
      display {
        description
        precision
      }
    }
  }

The first update will be the same as a get::

  {
    "subscribeChannel": {
      "value": {
        "string": "2.93893"
      },
      "status": {
        "quality": "VALID"
      },
      "display": {
        "description": "A Sine value generator",
        "precision": 5
      }
    }
  }

While subsequent updates will show a null status and display to indicate they have not changed::

  {
    "subscribeChannel": {
      "value": {
        "string": "-0.00000"
      },
      "status": null,
      "display": null
    }
  }

You can explore the graphiql interface, using Ctrl + . to autocomplete, and
using the documentation explorer on the right to see what else you can do.

Sim Plugin
----------

The sim plugin provides a number of channels that accept keyword args. For a
channel ``channel`` which takes up to 3 args, the allowed combinations are::

    ssim://channel
    ssim://channel(arg1)
    ssim://channel(arg1, arg2)
    ssim://channel(arg1, arg2, arg3)

Any unspecified arguments are defaulted.

Available channels:

- ssim://sine(min_value, max_value, steps, update_seconds, warning_percent, alarm_percent)
- ssim://sinewave(period_seconds, sample_wavelength, size, update_seconds, min_value, max_value, warning_percent, alarm_percent)


CA Plugin
---------

Coniql can provide values of Channel Access. To try this out, point it at some
running PVs on Diamond's network. If you need a softIoc, you can run one up
using the epicscorelibs Python package that is a dependency of coniql. Inside
the coniql directory type::

  pipenv run python -m epicscorelibs.ioc -m P=$(hostname -s): -d tests/soft_records.db

This will then let you get the current values of the PVs in that database file::

  query {
    getChannel(id: "ca://pc0105:longout") {
      value {
        string(units: true)
      }
    }
  }

You can also put to a PV::

  mutation {
    putChannel(id: "ca://pc0105:longout", value: "45") {
      value {
        string(units: true)
      }
    }
  }


PVA Plugin
----------

Coniql can also provide its values over pvAccess. To try this out you will need a
working installation of `EPICS 7 <https://epics.anl.gov/base/R7-0/index.php>`_. You can
then start a soft IOC, or add the PVA plugin to IOCs to expose PVs. The PVs work
like CA, but have the prefix ``pva://``
