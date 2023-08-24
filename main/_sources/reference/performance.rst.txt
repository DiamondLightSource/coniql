Performance
===========

Coniql has had much work done to have the best performance for Subscriptions, which are the primary use case
of most web GUIs, who are the primary consumers of Coniql data.

Coniql can handle approximately 2,000 updates per second. This was tested using 10Hz PVs, subscribing to
increasing numbers until updates were no longer being sent promptly.


Investigating Coniql Performance
--------------------------------


Method
^^^^^^

The primary method used for investigating Coniql's performance has been `py-spy <https://github.com/benfred/py-spy>`_.
This is a sampling profiler that can output speedscope-format data, which can then be viewed in the very nice
`Speedscope web UI <https://www.speedscope.app/>`_.

The profiles have been generates by first installing  ``py-spy``, then running the :doc:`benchmark` tests,
modifying the Bash script to launch  ``py-spy``, for example::

    CMD2="sleep 2;source $CONIQL_DIR/bin/activate;py-spy record --format speedscope --output speedscope-$(date +"%Y-%m-%d-%H:%M:%S") coniql"


An example speedscope can be found in this directory.


Findings
^^^^^^^^

Most of the time spent in processing results is done using ``async`` processing. The major performance gains so far have all come from
minimizing the amount of ``async`` calls that are made in our code. For example all of our Resolvers are now synchronous.
We do have to have some ``async`` calls, as we must use ``aioca`` to monitor PVs. These occur on initial calls to Query, Mutations,
and Subscriptions, in a stage before the Resolvers are called.

The current sampling shows that 80% of the time is spent in ``operation_task()``, which is a high level function inside Strawberry.
This code calls into the lower level ``graphql`` library for most of its runtime. Broadly, these calls handle the GraphQL protocol,
parsing the requested fields into calls to our library for data, then parsing that data back out to return the requested fields
to the client.

It is unclear why exactly this process seems to have so much overhead - further investigation is required.

Approxmately 1% of time is spent directly in Coniql code. Most of that is inside of the ``aioca`` callbacks. Additional performance gains in this
area are unlikely to be worthwhile as the possible gains are so small.
