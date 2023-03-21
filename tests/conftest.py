import asyncio
import json
import random
import string
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import ANY

import pytest
from aioca import purge_channel_caches

SOFT_RECORDS = str(Path(__file__).parent / "soft_records.db")

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12)) + ":"

BASE64_0_1688_2 = {
    "numberType": "FLOAT64",
    "base64": "AAAAAAAAAAA1XrpJDAL7PwAAAAAAAABA",
}


def wait_for_ioc(ioc):
    while True:
        line = ioc.stdout.readline()
        if "complete" in line:
            return


@pytest.fixture(scope="module")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def ioc_creator(pv_prefix=PV_PREFIX):
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


def run_ioc(process):
    yield process


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
    yield run_ioc(process)
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


longout_get_query = (
    """
query {
    getChannel(id: "ca://%slongout") {
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

ticking_subscription_result = [
    {
        "subscribeChannel": {
            "value": {"string": "0.00000 mm"},
            "display": {"precision": 5, "units": "mm"},
        }
    },
    {"subscribeChannel": {"value": {"string": "1.00000 mm"}, "display": None}},
    {"subscribeChannel": {"value": {"string": "2.00000 mm"}, "display": None}},
]
