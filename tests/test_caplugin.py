import time
from subprocess import Popen
from typing import Any, AsyncIterator, Dict, List

import pytest
from aioca import caput
from strawberry import Schema

from coniql.app import create_schema

from .conftest import (
    PV_PREFIX,
    base64_put_query,
    base64_put_query_result,
    check_put_timestamp,
    enum_get_query,
    enum_get_query_result,
    get_longout_subscription_query,
    ioc_creator,
    list_put_query,
    list_put_query_result,
    long_and_enum_put_query,
    long_and_enum_put_query_result,
    longout_get_query,
    longout_get_query_result,
    longout_str_get_query,
    longout_str_get_query_result,
    longout_subscription_result,
    nan_get_query,
    nan_get_query_result,
    run_ioc,
    ticking_subscription_query,
    ticking_subscription_result,
)


@pytest.fixture(scope="session")
def schema():
    return create_schema(False)


async def query_schema(schema: Schema, query: str):
    result = await schema.execute(query)
    return result.data


@pytest.mark.parametrize(
    "query, expected_result",
    [
        (longout_get_query, longout_get_query_result),
        (longout_str_get_query, longout_str_get_query_result),
        (enum_get_query, enum_get_query_result),
        (nan_get_query, nan_get_query_result),
    ],
    ids=["int_query", "str_query", "enum_query", "nan_query"],
)
async def test_schema_get_pv(
    ioc: Popen, schema: Schema, query: str, expected_result: str
):
    result = await query_schema(schema, query)
    assert result == expected_result


@pytest.mark.parametrize(
    "query, expected_result",
    [
        (long_and_enum_put_query, long_and_enum_put_query_result),
        (list_put_query, list_put_query_result),
        (base64_put_query, base64_put_query_result),
    ],
    ids=["long_and_enum_put", "list_put", "base64_put"],
)
async def test_schema_put_pv(
    ioc: Popen, schema: Schema, query: str, expected_result: str
):
    result = await query_schema(schema, query)
    assert result == expected_result
    check_put_timestamp(result)


@pytest.mark.asyncio
async def test_subscribe_disconnect(schema: Schema):
    pv_prefix = PV_PREFIX + "EXTRA:"
    ioc_process = ioc_creator(pv_prefix)
    run_ioc(ioc_process)
    query = get_longout_subscription_query(pv_prefix)
    results: List[Dict[str, Any]] = []
    resp = await schema.subscribe(query)
    assert isinstance(resp, AsyncIterator)
    async for result in resp:
        assert result.errors is None
        assert result.data
        if not results:
            # First response; now disconnect.
            results.append(result.data)
            ioc_process.communicate("exit()")
        else:
            # Second response; done.
            results.append(result.data)

            break
    assert len(results) == 2
    assert results[0] == longout_subscription_result[0]
    assert results[1] == longout_subscription_result[1]


@pytest.mark.asyncio
async def test_subscribe_ticking(ioc: Popen, schema: Schema):
    results = []
    await caput(PV_PREFIX + "ticking", 0.0)
    resp = await schema.subscribe(ticking_subscription_query)
    assert isinstance(resp, AsyncIterator)
    start = time.time()
    async for result in resp:
        if time.time() - start > 1.0:
            break
        results.append(result.data)
    for i in range(3):
        assert results[i] == ticking_subscription_result[i]
    assert len(results) == 3
