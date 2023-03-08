import asyncio
import json
import random
import string
import subprocess
import sys
from pathlib import Path

import pytest
from aioca import purge_channel_caches

SOFT_RECORDS = str(Path(__file__).parent / "soft_records.db")

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12)) + ":"

BASE64_0_1688_2 = dict(numberType="FLOAT64", base64="AAAAAAAAAAA1XrpJDAL7PwAAAAAAAABA")


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


@pytest.fixture(scope="session")
def int_query():
    return (
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


@pytest.fixture(scope="session")
def str_query():
    return (
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


@pytest.fixture(scope="session")
def nan_query():
    return (
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


@pytest.fixture(scope="session")
def enum_query():
    return (
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


def longout_subscribe_query(pv_prefix):
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


@pytest.fixture(scope="session")
def longout_subscribe():
    return longout_subscribe_query(PV_PREFIX)


def ticking_subscribe_query():
    return (
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


@pytest.fixture(scope="session")
def ticking_subscribe():
    return ticking_subscribe_query()


@pytest.fixture(scope="session")
def long_and_enum_put():
    return """
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


@pytest.fixture(scope="session")
def list_put():
    return (
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


@pytest.fixture(scope="session")
def base64_put():
    value = json.dumps(json.dumps(BASE64_0_1688_2))
    return """
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
        value,
    )
