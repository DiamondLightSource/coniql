import asyncio
import json
import random
import string
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast
from unittest.mock import ANY

import pytest
from aioca import purge_channel_caches
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL
from strawberry.subscriptions.protocols.graphql_transport_ws.types import (
    ConnectionAckMessage,
    ConnectionInitMessage,
    SubscribeMessage,
    SubscribeMessagePayload,
)
from strawberry.subscriptions.protocols.graphql_ws import (
    GQL_CONNECTION_ACK,
    GQL_CONNECTION_INIT,
    GQL_START,
)
from strawberry.subscriptions.protocols.graphql_ws.types import (
    OperationMessage,
    StartPayload,
)

from coniql.app import create_app
from coniql.caplugin import CAPlugin, CASubscriptionManager
from coniql.strawberry_schema import store_global

SOFT_RECORDS = str(Path(__file__).parent / "soft_records.db")

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12)) + ":"

BASE64_0_1688_2 = {
    "numberType": "FLOAT64",
    "base64": "AAAAAAAAAAA1XrpJDAL7PwAAAAAAAABA",
}

SUBSCRIPTION_TIMEOUT = 10


def wait_for_ioc(ioc):
    while True:
        line = ioc.stdout.readline()
        if "complete" in line:
            return


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def ioc_creator(pv_prefix=PV_PREFIX) -> subprocess.Popen:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "epicscorelibs.ioc",
            "-m",
            f"P={pv_prefix}",
            "-d",
            SOFT_RECORDS,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    wait_for_ioc(process)
    return process


def ioc_cleanup(process):
    purge_channel_caches()
    try:
        process.communicate("exit()")
    except ValueError:
        # Someone else already called communicate
        pass


@pytest.fixture(scope="module")
def ioc():
    process = ioc_creator()
    yield process
    ioc_cleanup(process)


def check_put_timestamp(result):
    thens = [
        datetime.fromisoformat(r["time"]["datetime"]) for r in result["putChannels"]
    ]

    now = datetime.now()
    for then in thens:
        diff = now - then
        # Shouldn't take more than this time to get the result of a put out
        assert diff.total_seconds() < 0.2


@pytest.fixture(scope="function")
async def client(aiohttp_client):
    cors = True
    debug = False
    graphiql = False
    connection_init_wait_timeout = timedelta(seconds=2)
    client = await aiohttp_client(
        create_app(cors, debug, graphiql, connection_init_wait_timeout)
    )
    return client


longout_get_query = (
    """
query {
    getChannel(id: "ca://%slongout") {
        id
        value {
            float
            string
        }
        display {
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
        }
        status {
            quality
        }
    }
}
"""
    % PV_PREFIX
)


longout_get_query_result = {
    "getChannel": {
        "id": f"ca://{PV_PREFIX}longout",
        "value": {"float": 42.0, "string": "42"},
        "display": {
            "widget": "TEXTINPUT",
            "controlRange": {"min": 10.0, "max": 90.0},
            "displayRange": {"min": 0.0, "max": 100.0},
            "alarmRange": {"min": 2.0, "max": 98.0},
            "warningRange": {"min": 5.0, "max": 96.0},
            "units": "",
            "precision": None,
            "form": None,
        },
        "status": {"quality": "VALID"},
    },
}


longout_str_get_query = (
    """
query {
    getChannel(id: "ca://%slongout.RTYP") {
        value {
            string
        }
    }
}
"""
    % PV_PREFIX
)


longout_str_get_query_result = {"getChannel": {"value": {"string": "longout"}}}

enum_get_query = (
    """
query {
    getChannel(id: "ca://%senum") {
        value {
            string
            float
        }
        display {
            choices
        }
    }
}
"""
    % PV_PREFIX
)


enum_get_query_result = {
    "getChannel": {
        "value": {"string": "nm", "float": 3.0},
        "display": {"choices": ["m", "mm", "um", "nm"]},
    }
}

nan_get_query = (
    """
query {
    getChannel(id: "ca://%snan") {
        value {
            float
        }
    }
}
"""
    % PV_PREFIX
)

nan_get_query_result = {"getChannel": {"value": {"float": None}}}

long_and_enum_put_query = """
mutation {
    putChannels(ids: ["ca://%slongout", "ca://%senum"], values: ["55", "1"]) {
        value {
            string
        }
        time {
            datetime
        }
    }
}
""" % (
    PV_PREFIX,
    PV_PREFIX,
)

long_and_enum_put_query_result = {
    "putChannels": [
        {"value": {"string": "55"}, "time": ANY},
        {"value": {"string": "mm"}, "time": ANY},
    ]
}

list_put_query = (
    """
mutation {
    putChannels(ids: ["ca://%swaveform"], values: ["[0, 1.688, 2]"]) {
        value {
            stringArray
            base64Array {
                numberType
                base64
            }
        }
        time {
            datetime
        }
    }
}
"""
    % PV_PREFIX
)

list_put_query_result = {
    "putChannels": [
        {
            "value": {
                "stringArray": ["0.0", "1.7", "2.0"],
                "base64Array": BASE64_0_1688_2,
            },
            "time": ANY,
        }
    ]
}

base64_put_query = """
mutation {
    putChannels(ids: ["ca://%swaveform"], values: [%s]) {
        value {
            stringArray
        }
        time {
            datetime
        }
    }
}
""" % (
    PV_PREFIX,
    json.dumps(json.dumps(BASE64_0_1688_2)),
)

base64_put_query_result = {
    "putChannels": [
        {
            "value": {"stringArray": ["0.0", "1.7", "2.0"]},
            "time": ANY,
        }
    ]
}


def get_longout_subscription_query(pv_prefix):
    return (
        """
subscription {
    subscribeChannel(id: "ca://%slongout") {
        value {
            float
        }
        status {
            quality
        }
    }
}
"""
        % pv_prefix
    )


longout_subscription_result = [
    {"subscribeChannel": {"value": {"float": 42.0}, "status": {"quality": "VALID"}}},
    {"subscribeChannel": {"value": None, "status": {"quality": "INVALID"}}},
]

ticking_subscription_query = (
    """
subscription {
    subscribeChannel(id: "ca://%sticking") {
        value {
            string(units: true)
            float
        }
        display {
            precision
            units
        }
    }
}
"""
    % PV_PREFIX
)


def get_ticking_subscription_result(startVal):
    return [
        {
            "subscribeChannel": {
                "value": {"string": f"{startVal}0000 mm", "float": startVal},
                "display": {"precision": 5, "units": "mm"},
            }
        },
        {
            "subscribeChannel": {
                "value": {"string": f"{startVal + 1}0000 mm", "float": startVal + 1},
                "display": None,
            }
        },
        {
            "subscribeChannel": {
                "value": {"string": f"{startVal + 2}0000 mm", "float": startVal + 2},
                "display": None,
            }
        },
    ]


subscribe_params = [
    (
        GRAPHQL_TRANSPORT_WS_PROTOCOL,
        ConnectionInitMessage().as_dict(),
        ConnectionAckMessage().as_dict(),
        SubscribeMessage(
            id="sub1",
            payload=SubscribeMessagePayload(query=ticking_subscription_query),
        ).as_dict(),
    ),
    (
        GRAPHQL_WS_PROTOCOL,
        OperationMessage(type=GQL_CONNECTION_INIT),
        OperationMessage(type=GQL_CONNECTION_ACK),
        OperationMessage(
            type=GQL_START,
            id="sub1",
            payload=StartPayload(query=ticking_subscription_query),
        ),
    ),
]


@pytest.fixture(
    scope="session",
    params=subscribe_params,
    ids=["graphql_transport_ws_protocol", "graphql_ws_protocol"],
)
def subscription_data(request):
    """Fixture for the possible subscription types"""
    return request.param


@pytest.fixture(autouse=True)
def clear_subscription_manager() -> None:
    """Reset the CASubscriptionManager inside the CAPlugin

    This ensures there's no record of PVs between tests"""

    ca_plugin: CAPlugin = cast(CAPlugin, store_global.plugins["ca"])
    ca_plugin.subscription_manager = CASubscriptionManager()
