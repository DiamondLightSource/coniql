import random
import string
import time
from dataclasses import dataclass
from unittest.mock import ANY

import numpy as np
import pytest
from p4p.nt import NTEnum, NTScalar
from p4p.server import Server
from p4p.server.asyncio import SharedPV
from tartiflette import Engine

from coniql.app import make_context


@dataclass
class SimIoc:
    double: SharedPV
    enum: SharedPV
    int_array: SharedPV
    server: Server


PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12))


@pytest.fixture
async def ioc():
    double = SharedPV(
        nt=NTScalar("d", display=True, control=True, valueAlarm=True), initial=2.0
    )

    @double.put
    def handle(pv, op):
        pv.post(op.value())  # just store and update subscribers
        op.done()

    enum = SharedPV(nt=NTEnum(), initial=dict(index=1, choices=["ZERO", "ONE", "TWO"]))

    int_array = SharedPV(
        nt=NTScalar("ai", display=True, control=True, valueAlarm=True), initial=[]
    )

    server = Server(
        providers=[
            {
                f"{PV_PREFIX}double": double,
                f"{PV_PREFIX}enum": enum,
                f"{PV_PREFIX}int_array": int_array,
            }
        ]
    )
    yield SimIoc(double, enum, int_array, server)
    server.stop()


@pytest.mark.asyncio
async def test_get_float_pv(engine: Engine, ioc: SimIoc):
    query = (
        """
query {
    getChannel(id: "pva://%sdouble") {
        value {
            float
            string
        }
        display {
            widget
        }
    }
}
"""
        % PV_PREFIX
    )
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(float=2.0, string="2.000"), display=dict(widget="TEXTINPUT"),
            ),
        )
    )


@pytest.mark.asyncio
async def test_get_enum_pv(engine: Engine, ioc: Server):
    query = (
        """
query {
    getChannel(id: "pva://%senum") {
        value {
            float
            string
        }
        display {
            widget
            choices
        }
    }
}
"""
        % PV_PREFIX
    )
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(float=1.0, string="ONE"),
                display=dict(widget="COMBO", choices=["ZERO", "ONE", "TWO"]),
            ),
        )
    )


@pytest.mark.asyncio
async def test_put_float_pv(engine: Engine, ioc: SimIoc):
    query = (
        """
mutation {
    putChannels(ids: ["pva://%sdouble"], values: ["40"]) {
        value {
            float
            string
        }
        status {
            quality
            message
        }
        time {
            seconds
        }
    }
}
"""
        % PV_PREFIX
    )
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            putChannels=[
                dict(
                    value=dict(float=40.0, string="40.000"),
                    status=dict(message="", quality="VALID"),
                    time=dict(seconds=ANY),
                )
            ]
        )
    )
    now = time.time()
    # Check that the timestamp is appropriately recent.
    assert now - result["data"]["putChannels"][0]["time"]["seconds"] < 0.3


@pytest.mark.asyncio
async def test_subscribe_int_pv(engine: Engine, ioc: SimIoc):
    query = (
        """
subscription {
    subscribeChannel(id: "pva://%sint_array") {
        value {
            stringArray
        }
    }
}
"""
        % PV_PREFIX
    )
    context = make_context()
    expected = np.ndarray([0], dtype=np.int32)
    async for result in engine.subscribe(query, context=context):
        assert result == dict(
            data=dict(subscribeChannel=dict(value=dict(stringArray=ANY)))
        )
        actual = result["data"]["subscribeChannel"]["value"]["stringArray"]
        assert ["%.3f" % x for x in expected] == actual
        num = len(actual)
        if num > 5:
            break
        expected = np.arange(num + 1, dtype=np.int32)
        ioc.int_array.post(expected)
