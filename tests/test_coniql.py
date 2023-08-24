import asyncio
import base64
import subprocess
import sys
import time
from pathlib import Path
from typing import AsyncIterator

import numpy as np
import pytest
from graphql import SourceLocation
from strawberry import Schema

from coniql import __version__
from coniql.app import create_schema

TEST_DIR = Path(__file__).resolve().parent

EXPECTED_SIM_SINE = [0.0, 2.938926261462366, 4.755282581475768]


@pytest.fixture(scope="session")
def schema():
    return create_schema(False)


@pytest.mark.asyncio
async def test_get_sim_sine(schema: Schema):
    query = """
query {
    getChannel(id: "ssim://sine(-5,5,10,1,60)") {
        value {
            float
            string
            base64Array {
                numberType
            }
            stringArray
        }
        display {
            widget
        }
    }
}
"""
    for i, x in enumerate(EXPECTED_SIM_SINE):
        if i != 0:
            await asyncio.sleep(1.0)
        result = await schema.execute(query)
        assert result.data == {
            "getChannel": {
                "value": {
                    "float": x,
                    "string": "%.5f" % x,
                    "base64Array": None,
                    "stringArray": None,
                },
                "display": {"widget": "TEXTUPDATE"},
            },
        }


@pytest.mark.asyncio
async def test_put_sim_sine_fails(schema: Schema):
    query = """
mutation {
    putChannels(ids: ["ssim://sine"], values: ["32"]) {
        value {
            float
        }
    }
}
"""
    result = await schema.execute(query)
    assert result.data is None
    assert result.errors is not None
    assert (
        result.errors[0].message
        == "Cannot put ['32'] to ['sine'], as they aren't writeable"
    )
    assert result.errors[0].locations == [SourceLocation(column=5, line=3)]
    assert result.errors[0].path == ["putChannels"]


@pytest.mark.asyncio
async def test_subscribe_sim_sine(schema: Schema):
    query = """
subscription {
    subscribeChannel(id: "ssim://sine") {
        value {
            float
        }
    }
}
"""
    results = []
    start = time.time()
    resp = await schema.subscribe(query)
    assert isinstance(resp, AsyncIterator)
    async for result in resp:
        results.append(result.data)
        if time.time() - start > 2:
            break
    for i, x in enumerate(EXPECTED_SIM_SINE):
        assert results[i] == {"subscribeChannel": {"value": {"float": x}}}
    assert len(results) == 3


@pytest.mark.asyncio
async def test_subscribe_ramp_wave(schema: Schema):
    query = """
subscription {
    subscribeChannel(id: "ssim://rampwave(3, 0.2)") {
        value {
            stringArray
        }
    }
}
"""
    results = []
    start = time.time()
    resp = await schema.subscribe(query)
    assert isinstance(resp, AsyncIterator)
    async for result in resp:
        results.append(result.data)
        if len(results) == 4:
            break
    # First result immediate, then takes 3x 0.2s
    assert time.time() - start - 0.6 < 0.2
    expected = [
        ["0.00000", "1.00000", "2.00000"],
        ["1.00000", "2.00000", "3.00000"],
        ["2.00000", "3.00000", "4.00000"],
        ["3.00000", "4.00000", "5.00000"],
    ]
    for i, x in enumerate(expected):
        assert results[i] == {"subscribeChannel": {"value": {"stringArray": x}}}


@pytest.mark.asyncio
async def test_get_sim_sinewave(schema: Schema):
    query = """
query {
    getChannel(id: "ssim://sinewave") {
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
    result = await schema.execute(query)
    assert result.data == {
        "getChannel": {
            "value": {
                "string": str(np.zeros(50)),
                "stringArray": ["%.5f" % x for x in np.zeros(10)],
                "base64Array": {
                    "numberType": "FLOAT64",
                    "base64": base64.b64encode(np.zeros(50).tobytes()).decode(),
                },
            }
        }
    }
    await asyncio.sleep(1.0)
    result = await schema.execute(query)
    assert result.data is not None
    b64s = result.data["getChannel"]["value"]["base64Array"]["base64"]
    str_value = np.frombuffer(base64.b64decode(b64s), dtype=np.float64)
    value = base64.b64decode(b64s)
    assert result.data == {
        "getChannel": {
            "value": {
                "string": str(str_value),
                "stringArray": ["%.5f" % x for x in str_value[:10]],
                "base64Array": {
                    "numberType": "FLOAT64",
                    "base64": base64.b64encode(value).decode(),
                },
            }
        }
    }


def test_cli_version():
    cmd = [sys.executable, "-m", "coniql", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__


def test_schema_contains_no_snake_case(schema: Schema):
    """Test that the Schema contains no snake_case members which may need to be
    converted to camelCase (as per GraphQL convention).

    Currently we set auto_camel_case=False when constructing the Schema, as currently
    there are no variables that need to be converted.

    If this test fails due to additions to the schema, this can probably be deleted
    (as long as we also re-enable auto_camel_case)"""

    introspected_schema = schema.introspect()

    for type in introspected_schema["__schema"]["types"]:
        name = type["name"]
        # Some inbuilt types with leading doule underscores exist, e.g. __Schema, __Type
        if name[0:2] != "__":
            assert "_" not in name

        if type["fields"] is not None:
            for field in type["fields"]:
                assert "_" not in field["name"]
