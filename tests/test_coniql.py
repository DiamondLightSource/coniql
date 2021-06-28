import asyncio
import base64
import time
from pathlib import Path

import numpy as np
import pytest
from tartiflette import Engine

from coniql.app import make_context

TEST_DIR = Path(__file__).resolve().parent


EXPECTED_SIM_SINE = [0.0, 2.938926261462366, 4.755282581475768]


@pytest.mark.asyncio
async def test_get_sim_sine(engine: Engine):
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
                    ),
                    display=dict(widget="TEXTUPDATE"),
                ),
            )
        )


@pytest.mark.asyncio
async def test_get_channels(engine: Engine):
    query = """
query {
    getChannels(filter:"ssim://sinewave(5*") {
        id
        display {
            description
        }
        value {
            stringArray(length:2)
        }
    }
}
"""
    context = make_context(TEST_DIR / "simdevices.coniql.yaml")
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            getChannels=[
                dict(
                    id="ssim://sinewave(5.0, 1000)",
                    display=dict(description="A low frequency sine wave"),
                    value=dict(stringArray=["0.00000", "0.00000"]),
                ),
            ]
        )
    )


@pytest.mark.asyncio
async def test_get_channel_config(engine: Engine):
    query = """
query {
    getChannelConfig(id:"ssim://sine") {
        readPv
        writePv
        description
        displayForm
        widget
    }
}
"""
    context = make_context(TEST_DIR / "simdevices.coniql.yaml")
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            getChannelConfig=dict(
                readPv="ssim://sine",
                writePv=None,
                description="A slow updating sine scalar value",
                displayForm=None,
                widget=None,
            )
        )
    )


@pytest.mark.asyncio
async def test_get_device(engine: Engine):
    query = """
query {
  getDevice(id:"Xspress3") {
    id
    children {
      name
      label
      child {
        ... on Channel {
          id
          value {
            float
          }
        }
        ... on Group {
          layout
        }
        ... on Device {
          id
        }
      }
    }
  }
}
"""
    context = make_context(TEST_DIR / "simdevices.coniql.yaml")
    result = await engine.execute(query, context=context)
    assert result == {
        "data": {
            "getDevice": {
                "id": "Xspress3",
                "children": [
                    {
                        "name": "Temperature",
                        "label": "Temperature",
                        "child": {"id": "ssim://sine(40, 50)", "value": {"float": 0}},
                    },
                    {
                        "name": "Channel1",
                        "label": "Channel1",
                        "child": {"id": "Xspress3.Channel1"},
                    },
                    {
                        "name": "Channel2",
                        "label": "Channel2",
                        "child": {"id": "Xspress3.Channel2"},
                    },
                    {
                        "name": "Channel3",
                        "label": "Channel3",
                        "child": {"id": "Xspress3.Channel3"},
                    },
                    {
                        "name": "Channel4",
                        "label": "Channel4",
                        "child": {"id": "Xspress3.Channel4"},
                    },
                ],
            }
        }
    }


@pytest.mark.asyncio
async def test_get_devices(engine: Engine):
    query = """
query {
  getDevices(filter:"Sine*") {
    id
    children(flatten:true) {
      name
      child {
        ... on Channel {
          id
          value {
            float
          }
        }
        ... on Group {
          layout
          children {
            name
          }
        }
        ... on Device {
          id
        }
      }
    }
  }
}
"""
    context = make_context(TEST_DIR / "simdevices.coniql.yaml")
    result = await engine.execute(query, context=context)
    assert result == {
        "data": {
            "getDevices": [
                {
                    "id": "Sine1",
                    "children": [
                        {
                            "name": "FastSine",
                            "child": {
                                "id": "ssim://sine(-10, 10, 100, 0.1)",
                                "value": {"float": 0.0},
                            },
                        },
                        {
                            "name": "SlowSine",
                            "child": {"id": "ssim://sine", "value": {"float": 0.0}},
                        },
                        {
                            "name": "Waves",
                            "child": {
                                "layout": "PLOT",
                                "children": [
                                    {"name": "HighFrequency"},
                                    {"name": "LowFrequency"},
                                ],
                            },
                        },
                        {
                            "name": "HighFrequency",
                            "child": {
                                "id": "ssim://sinewave(0.1, 1000)",
                                "value": {"float": None},
                            },
                        },
                        {
                            "name": "LowFrequency",
                            "child": {
                                "id": "ssim://sinewave(5.0, 1000)",
                                "value": {"float": None},
                            },
                        },
                    ],
                },
                {
                    "children": [
                        {
                            "name": "FastSine",
                            "child": {
                                "id": "ssim://sine(-10, 10, 100, 0.1)",
                                "value": {"float": 0.0},
                            },
                        },
                        {
                            "name": "SlowSine",
                            "child": {"id": "ssim://sine", "value": {"float": 0.0}},
                        },
                        {
                            "name": "Waves",
                            "child": {
                                "layout": "PLOT",
                                "children": [
                                    {"name": "HighFrequency"},
                                    {"name": "LowFrequency"},
                                ],
                            },
                        },
                        {
                            "name": "HighFrequency",
                            "child": {
                                "id": "ssim://sinewave(0.1, 1000)",
                                "value": {"float": None},
                            },
                        },
                        {
                            "name": "LowFrequency",
                            "child": {
                                "id": "ssim://sinewave(5.0, 1000)",
                                "value": {"float": None},
                            },
                        },
                    ],
                    "id": "Sine2",
                },
            ]
        }
    }


@pytest.mark.asyncio
async def test_put_sim_sine_fails(engine: Engine):
    query = """
mutation {
    putChannels(ids: ["ssim://sine"], values: ["32"]) {
        value {
            float
        }
    }
}
"""
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=None,
        errors=[
            dict(
                locations=[dict(column=5, line=3)],
                message="Cannot put ['32'] to ['sine'], as they aren't writeable",
                path=["putChannels"],
            )
        ],
    )


@pytest.mark.asyncio
async def test_subscribe_sim_sine(engine: Engine):
    query = """
subscription {
    subscribeChannel(id: "ssim://sine") {
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
async def test_subscribe_ramp_wave(engine: Engine):
    query = """
subscription {
    subscribeChannel(id: "ssim://rampwave(3, 0.2)") {
        value {
            stringArray
        }
    }
}
"""
    context = make_context()
    results = []
    start = time.time()
    async for result in engine.subscribe(query, context=context):
        results.append(result)
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
        assert results[i] == dict(
            data=dict(subscribeChannel=dict(value=dict(stringArray=x)))
        )


@pytest.mark.asyncio
async def test_get_sim_sinewave(engine: Engine):
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
                        base64=base64.b64encode(np.zeros(50).tobytes()).decode(),
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
