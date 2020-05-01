import asyncio
import base64
import time

import numpy as np
import pytest
from tartiflette import Engine

from coniql.app import make_context, make_engine


@pytest.fixture(scope="module")
async def engine():
    engine = make_engine()
    await engine.cook()
    yield engine


EXPECTED_SIM_SINE = [0.0, 2.938926261462366, 4.755282581475768]


@pytest.mark.asyncio
async def test_get_sim_sine(engine: Engine):
    query = """
query {
    getChannel(id: "sim://sine") {
        value {
            float
        }
    }
}
"""
    context = make_context()
    for i, x in enumerate(EXPECTED_SIM_SINE):
        if i != 0:
            await asyncio.sleep(1.0)
        result = await engine.execute(query, context=context)
        assert result == dict(data=dict(getChannel=dict(value=dict(float=x))))


@pytest.mark.asyncio
async def test_subscribe_sim_sine(engine: Engine):
    query = """
subscription {
    subscribeChannel(id: "sim://sine") {
        value {
            float
        }
    }
}
"""
    context = make_context()
    results = []
    start = time.time()
    async for result in engine.subscribe(query, context=context):
        results.append(result)
        if time.time() - start > 2:
            break
    for i, x in enumerate(EXPECTED_SIM_SINE):
        assert results[i] == dict(data=dict(subscribeChannel=dict(value=dict(float=x))))
    assert len(results) == 3


@pytest.mark.asyncio
async def test_get_sim_sinewave(engine: Engine):
    query = """
query {
    getChannel(id: "sim://sinewave") {
        value {
            string
            stringArray
            base64Array {
                numberType
                base64
            }
        }
    }
}
"""
    context = make_context()
    result = await engine.execute(query, context=context)
    expected = np.zeros(50)
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(
                    string=str(expected),
                    stringArray=["%.5f" % x for x in expected],
                    base64Array=dict(
                        numberType="FLOAT64", base64=base64.b64encode(expected).decode()
                    ),
                )
            )
        )
    )
