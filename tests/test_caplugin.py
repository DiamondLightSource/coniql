import asyncio
from subprocess import Popen
from typing import Any, AsyncIterator, Dict, List, Optional

import pytest
from strawberry import Schema

from coniql.app import create_schema

from .conftest import (
    PV_PREFIX,
    SUBSCRIPTION_TIMEOUT,
    base64_put_query,
    base64_put_query_result,
    check_put_timestamp,
    enum_get_query,
    enum_get_query_result,
    get_longout_subscription_query,
    get_ticking_subscription_result,
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
    results: List[Optional[Dict[str, Any]]] = []
    resp = await schema.subscribe(ticking_subscription_query)
    assert isinstance(resp, AsyncIterator)
    count = 0
    while True:
        if count > 2:
            break
        # Set a timeout on wait for a response as otherwise this call will
        # block forever unless the schema.subscribe() receives data
        result = await asyncio.wait_for(resp.__anext__(), timeout=SUBSCRIPTION_TIMEOUT)
        results.append(result.data)
        count += 1
    assert len(results) == 3
    # Determine the starting value in the subscription
    startSub = results[0]
    assert startSub
    startVal = startSub["subscribeChannel"]["value"]["float"]
    subscription_result = get_ticking_subscription_result(startVal)
    for i in range(3):
        assert results[i] == subscription_result[i]
