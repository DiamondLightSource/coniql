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
    getChannel(id: "sim://sine(-5,5,10,1,60)") {
        value {
            float
            string
            base64Array {
                numberType
            }
            stringArray
        }
    }
}
"""
    context = make_context()
    for i, x in enumerate(EXPECTED_SIM_SINE):
        if i != 0:
            await asyncio.sleep(1.0)
        result = await engine.execute(query, context=context)
        assert result == dict(
            data=dict(
                getChannel=dict(
                    value=dict(
                        float=x, string="%.5f" % x, base64Array=None, stringArray=None
                    )
                )
            )
        )


@pytest.mark.asyncio
async def test_put_sim_sine_fails(engine: Engine):
    query = """
mutation {
    putChannel(id: "sim://sine", value: "32") {
        value {
            float
        }
    }
}
"""
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(putChannel=None),
        errors=[
            dict(
                locations=[dict(column=5, line=3)],
                message="Cannot put '32' to sim://sine, as it isn't writeable",
                path=["putChannel"],
            )
        ],
    )


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
            stringArray(length: 10)
            base64Array(length: 100) {
                numberType
                base64
            }
        }
    }
}
"""
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(
                    string=str(np.zeros(50)),
                    stringArray=["%.5f" % x for x in np.zeros(10)],
                    base64Array=dict(
                        numberType="FLOAT64",
                        base64=base64.b64encode(np.zeros(50)).decode(),
                    ),
                )
            )
        )
    )
    await asyncio.sleep(1.0)
    result = await engine.execute(query, context=context)
    b64s = result["data"]["getChannel"]["value"]["base64Array"]["base64"]
    value = np.frombuffer(base64.b64decode(b64s), dtype=np.float64)
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(
                    string=str(value),
                    stringArray=["%.5f" % x for x in value[:10]],
                    base64Array=dict(
                        numberType="FLOAT64", base64=base64.b64encode(value).decode(),
                    ),
                )
            )
        )
    )
