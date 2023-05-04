import asyncio
import time
from subprocess import Popen
from typing import Any, Dict, List

import pytest
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

from .conftest import (
    PV_PREFIX,
    base64_put_query,
    base64_put_query_result,
    check_put_timestamp,
    enum_get_query,
    enum_get_query_result,
    get_longout_subscription_query,
    ioc_cleanup,
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
async def test_aiohttp_client_get_pv(
    ioc: Popen, client: TestClient, query: str, expected_result: str
):
    resp = await client.get("/ws", params={"query": query})
    assert resp.status == 200
    result = await resp.json()
    assert result["data"] == expected_result


@pytest.mark.parametrize(
    "query, expected_result",
    [
        (long_and_enum_put_query, long_and_enum_put_query_result),
        (list_put_query, list_put_query_result),
        (base64_put_query, base64_put_query_result),
    ],
    ids=["long_and_enum_query", "list_query", "base64_query"],
)
async def test_aiohttp_client_put_pv(
    ioc: Popen, client: TestClient, query: str, expected_result: str
):
    resp = await client.post("/ws", json={"query": query})
    result = await resp.json()
    assert result["data"] == expected_result
    check_put_timestamp(result["data"])


@pytest.mark.asyncio
async def test_subscribe_disconnect(client: TestClient):
    pv_prefix = PV_PREFIX + "EXTRA:"
    ioc_process = ioc_creator(pv_prefix)
    run_ioc(ioc_process)
    query = get_longout_subscription_query(pv_prefix)
    results: List[Dict[str, Any]] = []
    async with client.ws_connect(
        "/ws", protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL]
    ) as ws:
        await ws.send_json(ConnectionInitMessage().as_dict())

        response = await ws.receive_json()
        assert response == ConnectionAckMessage().as_dict()

        await asyncio.sleep(0.1)
        await ws.send_json(
            SubscribeMessage(
                id="sub1",
                payload=SubscribeMessagePayload(query=query),
            ).as_dict()
        )
        while True:
            result = await ws.receive_json()
            if not results:
                # First response; now disconnect.
                results.append(result["payload"]["data"])
                ioc_process.communicate("exit()")
            else:
                # Second response; done.
                results.append(result["payload"]["data"])
                break

        await ws.close()
        assert ws.closed

    assert len(results) == 2
    assert results[0] == longout_subscription_result[0]
    assert results[1] == longout_subscription_result[1]
    ioc_cleanup(ioc_process)


subscribe_params = [
    (
        GRAPHQL_TRANSPORT_WS_PROTOCOL,
        ConnectionInitMessage().as_dict(),
        ConnectionAckMessage().as_dict(),
        SubscribeMessage(
            id="sub1",
            payload=SubscribeMessagePayload(query=ticking_subscription_query),
        ).as_dict(),
    ),
    (
        GRAPHQL_WS_PROTOCOL,
        OperationMessage(type=GQL_CONNECTION_INIT),
        OperationMessage(type=GQL_CONNECTION_ACK),
        OperationMessage(
            type=GQL_START,
            id="sub1",
            payload=StartPayload(query=ticking_subscription_query),
        ),
    ),
]


@pytest.mark.parametrize(
    "ws_protocol,msg_init,msg_ack,msg_send",
    subscribe_params,
    ids=["graphql_transport_ws_protocol", "graphql_ws_protocol"],
)
@pytest.mark.asyncio
async def test_subscribe_pv(
    ioc: Popen,
    client: TestClient,
    ws_protocol,
    msg_init,
    msg_ack,
    msg_send,
):
    results = []

    async with client.ws_connect("/ws", protocols=[ws_protocol]) as ws:
        await ws.send_json(msg_init)
        response = await ws.receive_json()
        assert response == msg_ack
        await asyncio.sleep(0.1)
        start = time.time()
        await ws.send_json(msg_send)
        await caput(PV_PREFIX + "ticking", 0.0)
        while True:
            if time.time() - start > 0.5:
                break
            result = await ws.receive_json()
            if result["type"] == GQL_CONNECTION_KEEP_ALIVE:
                continue
            results.append(result["payload"]["data"])

        await ws.close()
        assert ws.closed
    assert len(results) == 3
    for i in range(3):
        assert results[i] == ticking_subscription_result[i]
