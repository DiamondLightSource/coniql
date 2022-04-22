import json
import math
import random
import string
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from subprocess import Popen
from typing import Any, Dict, List
from unittest.mock import ANY

import pytest
from aioca import caget, purge_channel_caches
from tartiflette import Engine

from coniql.app import make_context

SOFT_RECORDS = str(Path(__file__).parent / "soft_records.db")

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12)) + ":"


@pytest.fixture
def ioc():
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "epicscorelibs.ioc",
            "-m",
            f"P={PV_PREFIX}",
            "-d",
            SOFT_RECORDS,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    yield process
    purge_channel_caches()
    try:
        process.communicate("exit()")
    except ValueError:
        # Someone else already called communicate
        pass


def wait_for_ioc(ioc):
    while True:
        line = ioc.stdout.readline()
        if "complete" in line:
            return


@pytest.mark.asyncio
async def test_get_int_pv(engine: Engine, ioc: Popen):
    query = (
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
    result = await engine.execute(query, context=make_context())
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(float=42.0, string="42"),
                display=dict(
                    widget="TEXTINPUT",
                    controlRange=dict(min=10.0, max=90.0),
                    displayRange=dict(min=0.0, max=100.0),
                    alarmRange=dict(min=2.0, max=98.0),
                    warningRange=dict(min=5.0, max=96.0),
                    units="",
                    precision=None,
                    form=None,
                ),
                status=dict(quality="VALID"),
            ),
        )
    )


@pytest.mark.asyncio
async def test_get_str_pv(engine: Engine, ioc: Popen):
    query = (
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
    result = await engine.execute(query, context=make_context())
    assert result == dict(data=dict(getChannel=dict(value=dict(string="longout"))))


@pytest.mark.asyncio
async def test_get_nan_pv(engine: Engine, ioc: Popen):
    query = (
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
    val = await caget(PV_PREFIX + "nan")
    assert math.isnan(val)
    result = await engine.execute(query, context=make_context())
    assert result == dict(data=dict(getChannel=dict(value=dict(float=None))))


@pytest.mark.asyncio
async def test_get_enum_pv(engine: Engine, ioc: Popen):
    query = (
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
    result = await engine.execute(query, context=make_context())
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(string="nm", float=3.0),
                display=dict(choices=["m", "mm", "um", "nm"]),
            )
        )
    )


@pytest.mark.asyncio
async def test_subscribe_disconnect(engine: Engine, ioc: Popen):
    query = (
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
        % PV_PREFIX
    )
    results: List[Dict[str, Any]] = []
    wait_for_ioc(ioc)
    async for result in engine.subscribe(query, context=make_context()):
        if not results:
            # First response; now disconnect.
            results.append(result)
            ioc.communicate("exit()")
        else:
            # Second response; done.
            results.append(result)
            break

    assert len(results) == 2
    assert results[0] == dict(
        data=dict(
            subscribeChannel=dict(value=dict(float=42), status=dict(quality="VALID"))
        )
    )
    assert results[1] == dict(
        data=dict(subscribeChannel=dict(value=None, status=dict(quality="INVALID")))
    )


@pytest.mark.asyncio
async def test_subscribe_ticking(engine: Engine, ioc: Popen):
    query = (
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
    results = []
    wait_for_ioc(ioc)
    start = time.time()
    async for result in engine.subscribe(query, context=make_context()):
        results.append(result)
        if time.time() - start > 0.9:
            break
    for i in range(3):
        display = None
        if i == 0:
            display = dict(precision=5, units="mm")
        assert results[i] == dict(
            data=dict(
                subscribeChannel=dict(value=dict(string="%.5f mm" % i), display=display)
            )
        )
    assert len(results) == 3


@pytest.mark.asyncio
async def test_put_long_and_enum(engine: Engine, ioc: Popen):
    query = """
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
    result = await engine.execute(query, context=make_context())
    assert result == dict(
        data=dict(
            putChannels=[
                dict(value=dict(string="55"), time=ANY),
                dict(value=dict(string="mm"), time=ANY),
            ]
        )
    )
    thens = [
        datetime.fromisoformat(r["time"]["datetime"])
        for r in result["data"]["putChannels"]
    ]
    now = datetime.now()
    for then in thens:
        diff = now - then
        # Shouldn't take more than this time to get the result of a put out
        assert diff.total_seconds() < 0.2


BASE64_0_1688_2 = dict(numberType="FLOAT64", base64="AAAAAAAAAAA1XrpJDAL7PwAAAAAAAABA")


@pytest.mark.asyncio
async def test_put_list(engine: Engine, ioc: Popen):
    query = (
        r"""
mutation {
    putChannels(ids: ["ca://%swaveform"], values: ["[0, 1.688, \"2\"]"]) {
        value {
            stringArray
            base64Array {
                numberType
                base64
            }
        }
    }
}
"""
        % PV_PREFIX
    )
    result = await engine.execute(query, context=make_context())
    assert result == dict(
        data=dict(
            putChannels=[
                dict(
                    value=dict(
                        stringArray=["0.0", "1.7", "2.0"], base64Array=BASE64_0_1688_2
                    )
                )
            ]
        )
    )


@pytest.mark.asyncio
async def test_put_base64(engine: Engine, ioc: Popen):
    # first dump gives {"key": "value"}, a json string
    # second dump gives \{\"key\": \"value\"\}, an escaped json string
    value = json.dumps(json.dumps(BASE64_0_1688_2))
    query = r"""
mutation {
    putChannels(ids: ["ca://%swaveform"], values: [%s]) {
        value {
            stringArray
        }
    }
}
""" % (
        PV_PREFIX,
        value,
    )
    result = await engine.execute(query, context=make_context())
    assert result == dict(
        data=dict(putChannels=[dict(value=dict(stringArray=["0.0", "1.7", "2.0"]))])
    )
