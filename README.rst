coniql
======

Control system interface in GraphQL

Installation
------------

After cloning from Github/Gitlab, install epics base in /scratch from:

https://epics-controls.org/download/base/base-7.0.2.2.tar.gz

cd to the directory and type make

Then install the depenencies using instructions from:

https://confluence.diamond.ac.uk/display/SSCC/Python+3+User+Documentation

Then you can run the example::
    
    PYTHONPATH=. pipenv run python coniql/server.py

And see the grphiql interface here:

http://localhost:8000/graphiql

With something like::

    subscription {
      subscribeChannel(id: "TMC43-TS-IOC-01:AI") {
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
