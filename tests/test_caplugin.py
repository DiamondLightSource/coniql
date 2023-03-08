import math
import time
from datetime import datetime
from subprocess import Popen
from typing import Any, Dict, List
from unittest.mock import ANY

import pytest
from aioca import caget, caput
from strawberry import Schema

from coniql.app import create_schema

from .conftest import (
    BASE64_0_1688_2,
    PV_PREFIX,
    ioc_creator,
    longout_subscribe_query,
    run_ioc,
)


@pytest.fixture(scope="session")
def schema():
    return create_schema(False)


@pytest.mark.asyncio
async def test_get_int_pv(ioc: Popen, schema: Schema, int_query: str):
    query = int_query
    result = await schema.execute(query)
    assert result.errors is None
    assert result.data == dict(
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


@pytest.mark.asyncio
async def test_get_str_pv(ioc: Popen, schema: Schema, str_query: str):
    query = str_query
    result = await schema.execute(query)
    assert result.errors is None
    assert result.data == dict(getChannel=dict(value=dict(string="longout")))


@pytest.mark.asyncio
async def test_get_nan_pv(ioc: Popen, schema: Schema, nan_query):
    query = nan_query
    val = await caget(PV_PREFIX + "nan")
    assert math.isnan(val)
    result = await schema.execute(query)
    assert result.errors is None
    assert result.data == dict(getChannel=dict(value=dict(float=None)))


@pytest.mark.asyncio
async def test_get_enum_pv(ioc: Popen, schema: Schema, enum_query: str):
    query = enum_query
    result = await schema.execute(query)
    assert result.errors is None
    assert result.data == dict(
        getChannel=dict(
            value=dict(string="nm", float=3.0),
            display=dict(choices=["m", "mm", "um", "nm"]),
        )
    )


@pytest.mark.asyncio
async def test_put_long_and_enum(ioc: Popen, schema: Schema, long_and_enum_put: str):
    query = long_and_enum_put
    result = await schema.execute(query)
    assert result.data == dict(
        putChannels=[
            dict(value=dict(string="55"), time=ANY),
            dict(value=dict(string="mm"), time=ANY),
        ]
    )
    thens = [
        datetime.fromisoformat(r["time"]["datetime"])
        for r in result.data["putChannels"]
    ]
    now = datetime.now()
    for then in thens:
        diff = now - then
        # Shouldn't take more than this time to get the result of a put out
        assert diff.total_seconds() < 0.2


@pytest.mark.asyncio
async def test_put_list(ioc: Popen, schema: Schema, list_put: str):
    query = list_put
    result = await schema.execute(query)
    assert result.data == dict(
        putChannels=[
            dict(
                value=dict(
                    stringArray=["0.0", "1.7", "2.0"], base64Array=BASE64_0_1688_2
                ),
                time=ANY,
            )
        ]
    )


@pytest.mark.asyncio
async def test_put_base64(ioc: Popen, schema: Schema, base64_put: str):
    # first dump gives {"key": "value"}, a json string
    # second dump gives \{\"key\": \"value\"\}, an escaped json string
    query = base64_put
    result = await schema.execute(query)
    assert result.data == dict(
        putChannels=[dict(value=dict(stringArray=["0.0", "1.7", "2.0"]), time=ANY)]
    )


@pytest.mark.asyncio
async def test_subscribe_disconnect(schema: Schema):
    pv_prefix = PV_PREFIX + "EXTRA:"
    ioc_process = ioc_creator(pv_prefix)
    run_ioc(ioc_process)
    query = longout_subscribe_query(pv_prefix)
    results: List[Dict[str, Any]] = []
    resp = await schema.subscribe(query)
    async for result in resp:
        assert result.errors is None
        if not results:
            # First response; now disconnect.
            results.append(result.data)
            ioc_process.communicate("exit()")
        else:
            # Second response; done.
            results.append(result.data)

            break
    assert len(results) == 2
    assert results[0] == dict(
        subscribeChannel=dict(value=dict(float=42), status=dict(quality="VALID"))
    )
    assert results[1] == dict(
        subscribeChannel=dict(value=None, status=dict(quality="INVALID"))
    )


@pytest.mark.asyncio
async def test_subscribe_ticking(ioc: Popen, schema: Schema, ticking_subscribe: str):
    query = ticking_subscribe
    results = []
    await caput(PV_PREFIX + "ticking", 0.0)
    start = time.time()
    resp = await schema.subscribe(query)
    async for result in resp:
        if time.time() - start > 1.0:
            break
        results.append(result.data)
    for i in range(3):
        display = None
        if i == 0:
            display = dict(precision=5, units="mm")
        assert results[i] == dict(
            subscribeChannel=dict(value=dict(string="%.5f mm" % i), display=display)
        )
    assert len(results) == 3
