import asyncio
import time
from datetime import datetime
from subprocess import Popen
from typing import Any, Dict, List, Optional
from unittest.mock import ANY

import pytest
import strawberry
from aioca import caput
from aiohttp.test_utils import TestClient
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL
from strawberry.subscriptions.protocols.graphql_transport_ws.types import (
    ConnectionAckMessage,
    ConnectionInitMessage,
    SubscribeMessage,
    SubscribeMessagePayload,
)
from strawberry.subscriptions.protocols.graphql_ws import (
    GQL_CONNECTION_ACK,
    GQL_CONNECTION_INIT,
    GQL_CONNECTION_KEEP_ALIVE,
    GQL_START,
)
from strawberry.subscriptions.protocols.graphql_ws.types import (
    OperationMessage,
    StartPayload,
)

from coniql.app import create_app, create_schema

from .conftest import (
    BASE64_0_1688_2,
    PV_PREFIX,
    ioc_creator,
    longout_subscribe_query,
    run_ioc,
    ticking_subscribe_query,
)


@pytest.fixture(scope="session")
def schema() -> strawberry.Schema:
    return create_schema(False)


@pytest.fixture()
async def client(aiohttp_client) -> TestClient:
    cors = True
    debug = False
    graphiql = False
    client = await aiohttp_client(create_app(cors, debug, graphiql))
    return client


async def query_aio_httpclient(client: TestClient, query: str):
    resp = await client.get("/ws", params={"query": query})
    result = await resp.json()
    return result["data"]


async def post_aio_httpclient(client: TestClient, query: str):
    resp = await client.post("/ws", json={"query": query})
    result = await resp.json()
    return result["data"]


async def query_schema(schema: strawberry.Schema, query: str):
    result = await schema.execute(query)
    return result.data


@pytest.fixture()
async def client_get_int_pv(client: TestClient, int_query: str):
    return await query_aio_httpclient(client, int_query)


@pytest.fixture()
async def schema_get_int_pv(schema: strawberry.Schema, int_query: str):
    return await query_schema(schema, int_query)


@pytest.fixture()
async def client_get_str_pv(client: TestClient, str_query: str):
    return await query_aio_httpclient(client, str_query)


@pytest.fixture()
async def schema_get_str_pv(schema: strawberry.Schema, str_query: str):
    return await query_schema(schema, str_query)


@pytest.fixture()
async def client_get_nan_pv(client: TestClient, nan_query: str):
    return await query_aio_httpclient(client, nan_query)


@pytest.fixture()
async def schema_get_nan_pv(schema: strawberry.Schema, nan_query: str):
    return await query_schema(schema, nan_query)


@pytest.fixture()
async def client_get_enum_pv(client: TestClient, enum_query: str):
    return await query_aio_httpclient(client, enum_query)


@pytest.fixture()
async def schema_get_enum_pv(schema: strawberry.Schema, enum_query: str):
    return await query_schema(schema, enum_query)


@pytest.fixture()
async def client_put_long_and_enum_pv(client: TestClient, long_and_enum_put: str):
    return await post_aio_httpclient(client, long_and_enum_put)


@pytest.fixture()
async def schema_put_long_and_enum_pv(
    schema: strawberry.Schema, long_and_enum_put: str
):
    return await query_schema(schema, long_and_enum_put)


@pytest.fixture()
async def client_put_list_pv(client: TestClient, list_put: str):
    return await post_aio_httpclient(client, list_put)


@pytest.fixture()
async def schema_put_list_pv(schema: strawberry.Schema, list_put: str):
    return await query_schema(schema, list_put)


@pytest.fixture()
async def client_put_base64_pv(client: TestClient, base64_put: str):
    return await post_aio_httpclient(client, base64_put)


@pytest.fixture()
async def schema_put_base64_pv(schema: strawberry.Schema, base64_put: str):
    return await query_schema(schema, base64_put)


int_pv_result = dict(
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

str_pv_result = dict(getChannel=dict(value=dict(string="longout")))

nan_pv_result = dict(getChannel=dict(value=dict(float=None)))

enum_pv_result = dict(
    getChannel=dict(
        value=dict(string="nm", float=3.0),
        display=dict(choices=["m", "mm", "um", "nm"]),
    )
)

long_and_enum_put_results = dict(
    putChannels=[
        dict(value=dict(string="55"), time=ANY),
        dict(value=dict(string="mm"), time=ANY),
    ]
)

list_put_results = dict(
    putChannels=[
        dict(
            value=dict(stringArray=["0.0", "1.7", "2.0"], base64Array=BASE64_0_1688_2),
            time=ANY,
        )
    ]
)

base64_put_results = dict(
    putChannels=[
        dict(
            value=dict(stringArray=["0.0", "1.7", "2.0"]),
            time=ANY,
        )
    ]
)

get_pv_tests_params = [
    ("client_get_int_pv", int_pv_result),
    ("schema_get_int_pv", int_pv_result),
    ("client_get_str_pv", str_pv_result),
    ("schema_get_str_pv", str_pv_result),
    ("client_get_enum_pv", enum_pv_result),
    ("schema_get_enum_pv", enum_pv_result),
    ("client_get_nan_pv", nan_pv_result),
    ("schema_get_nan_pv", nan_pv_result),
]


@pytest.mark.parametrize("run_fixture, expected_result", get_pv_tests_params)
def test_get_pv(ioc: Popen, run_fixture, expected_result, request):
    result = request.getfixturevalue(run_fixture)
    assert result == expected_result


put_pv_tests_params = [
    ("client_put_long_and_enum_pv", long_and_enum_put_results),
    ("schema_put_long_and_enum_pv", long_and_enum_put_results),
    ("client_put_list_pv", list_put_results),
    ("schema_put_list_pv", list_put_results),
    ("client_put_base64_pv", base64_put_results),
    ("schema_put_base64_pv", base64_put_results),
]


@pytest.mark.parametrize("run_fixture, expected_result", put_pv_tests_params)
def test_put_pv(ioc: Popen, run_fixture, expected_result, request):
    result = request.getfixturevalue(run_fixture)
    assert result == expected_result
    thens = [
        datetime.fromisoformat(r["time"]["datetime"]) for r in result["putChannels"]
    ]

    now = datetime.now()
    for then in thens:
        diff = now - then
        # Shouldn't take more than this time to get the result of a put out
        assert diff.total_seconds() < 0.2


async def subscribe_aio_httpclient(
    client: TestClient, ioc_process, timer, ws_protocol, msg_init, msg_ack, msg_send
):
    """Create a subscription to the client via a websocket. The message types
    are configured to allow compatibility with different wesocket protocols"""
    results: List[Dict[str, Any]] = []
    start = time.time()
    async with client.ws_connect("/ws", protocols=[ws_protocol]) as ws:
        await ws.send_json(msg_init)
        response = await ws.receive_json()
        assert response == msg_ack
        await asyncio.sleep(0.1)
        await ws.send_json(msg_send)
        while True:
            if timer is not None:
                if time.time() - start > timer:
                    break
            result = await ws.receive_json()
            if result["type"] == GQL_CONNECTION_KEEP_ALIVE:
                continue
            if not results:
                # First response; now disconnect.
                results.append(result["payload"]["data"])
                if ioc_process:
                    ioc_process.communicate("exit()")
            else:
                # Second response; done.
                results.append(result["payload"]["data"])
                if timer is None:
                    break
        await ws.close()
    return results


@pytest.fixture()
async def client_subscribe_disconnect(client: TestClient):
    """Create and run a new IOC for this test so that the disconnect
    does not affect later tests"""
    pv_prefix = PV_PREFIX + "EXTRA:"
    query = longout_subscribe_query(pv_prefix)
    ioc_process = ioc_creator(pv_prefix)
    run_ioc(ioc_process)
    timer = None
    return await subscribe_aio_httpclient(
        client,
        ioc_process,
        timer,
        GRAPHQL_TRANSPORT_WS_PROTOCOL,
        ConnectionInitMessage().as_dict(),
        ConnectionAckMessage().as_dict(),
        SubscribeMessage(
            id="sub1",
            payload=SubscribeMessagePayload(query=query),
        ).as_dict(),
    )


@pytest.fixture()
async def client_subscribe_ticking_graphql_ws(client: TestClient):
    await caput(PV_PREFIX + "ticking", 0.0)
    timer = 0.5
    return await subscribe_aio_httpclient(
        client,
        None,
        timer,
        GRAPHQL_WS_PROTOCOL,
        OperationMessage(type=GQL_CONNECTION_INIT),
        OperationMessage(type=GQL_CONNECTION_ACK),
        OperationMessage(
            type=GQL_START,
            id="sub1",
            payload=StartPayload(query=ticking_subscribe_query()),
        ),
    )


@pytest.fixture()
async def client_subscribe_ticking_graphql_transport_ws(client: TestClient):
    await caput(PV_PREFIX + "ticking", 0.0)
    timer = 0.5
    return await subscribe_aio_httpclient(
        client,
        None,
        timer,
        GRAPHQL_TRANSPORT_WS_PROTOCOL,
        ConnectionInitMessage().as_dict(),
        ConnectionAckMessage().as_dict(),
        SubscribeMessage(
            id="sub1",
            payload=SubscribeMessagePayload(query=ticking_subscribe_query()),
        ).as_dict(),
    )


async def subscribe_schema(
    schema: strawberry.Schema,
    query: str,
    ioc_process: Optional[Popen],
    timer: Optional[float],
):
    results: List[Dict[str, Any]] = []
    start = time.time()
    resp = await schema.subscribe(query)
    async for result in resp:
        if timer is not None:
            if time.time() - start > timer:
                break
        if not results:
            # First response; now disconnect.
            results.append(result.data)
            if ioc_process:
                ioc_process.communicate("exit()")
        else:
            # Second response; done.
            results.append(result.data)
            if timer is None:
                break
    return results


@pytest.fixture()
async def schema_subscribe_disconnect(schema: strawberry.Schema):
    """Create and run a new IOC for this test so that the disconnect
    does not affect later tests"""
    pv_prefix = PV_PREFIX + "EXTRA:"
    query = longout_subscribe_query(pv_prefix)
    ioc_process = ioc_creator(pv_prefix)
    run_ioc(ioc_process)
    timer = None
    return await subscribe_schema(schema, query, ioc_process, timer)


@pytest.fixture()
async def schema_subscribe_ticking(schema: strawberry.Schema, ticking_subscribe: str):
    await caput(PV_PREFIX + "ticking", 0.0)
    timer = 1.0
    return await subscribe_schema(schema, ticking_subscribe, None, timer)


longout_subscribe_result = [
    dict(subscribeChannel=dict(value=dict(float=42.0), status=dict(quality="VALID"))),
    dict(subscribeChannel=dict(value=None, status=dict(quality="INVALID"))),
]

ticking_subscribe_result = [
    dict(
        subscribeChannel=dict(
            value=dict(string="0.00000 mm"), display=dict(precision=5, units="mm")
        )
    ),
    dict(subscribeChannel=dict(value=dict(string="1.00000 mm"), display=None)),
    dict(subscribeChannel=dict(value=dict(string="2.00000 mm"), display=None)),
]


subscribe_pv_tests_params = [
    ("client_subscribe_disconnect", longout_subscribe_result),
    ("schema_subscribe_disconnect", longout_subscribe_result),
    ("client_subscribe_ticking_graphql_ws", ticking_subscribe_result),
    ("client_subscribe_ticking_graphql_transport_ws", ticking_subscribe_result),
    ("schema_subscribe_ticking", ticking_subscribe_result),
]


@pytest.mark.parametrize("run_fixture, expected_result", subscribe_pv_tests_params)
def test_subscribe_pv(ioc: Popen, run_fixture, expected_result, request):
    results = request.getfixturevalue(run_fixture)
    assert len(results) == len(expected_result)
    for i in range(len(results)):
        assert results[i] == expected_result[i]
