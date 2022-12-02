import asyncio
import math
import time
from datetime import datetime
from subprocess import Popen
from typing import Any, Dict, List
from unittest.mock import ANY

import pytest
from aioca import caget, caput
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

from coniql.app import create_app

from .conftest import BASE64_0_1688_2, PV_PREFIX


@pytest.fixture(scope="function")
async def client(aiohttp_client):
    cors = True
    debug = False
    client = await aiohttp_client(create_app(cors, debug))
    return client


@pytest.mark.asyncio
async def test_get_int_pv(ioc: Popen, client, int_query):
    query = int_query
    resp = await client.get("/ws", params={"query": query})
    assert resp.status == 200
    result = await resp.json()
    assert result == dict(
        data=dict(
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
    )


@pytest.mark.asyncio
async def test_get_str_pv(ioc: Popen, client, str_query):
    query = str_query
    resp = await client.get("/ws", params={"query": query})
    assert resp.status == 200
    result = await resp.json()
    assert result == dict(data=dict(getChannel=dict(value=dict(string="longout"))))


@pytest.mark.asyncio
async def test_get_nan_pv(ioc: Popen, client, nan_query):
    query = nan_query
    val = await caget(PV_PREFIX + "nan")
    assert math.isnan(val)
    resp = await client.get("/ws", params={"query": query})
    assert resp.status == 200
    result = await resp.json()
    assert result == dict(data=dict(getChannel=dict(value=dict(float=None))))


@pytest.mark.asyncio
async def test_get_enum_pv(ioc: Popen, client, enum_query):
    query = enum_query
    resp = await client.get("/ws", params={"query": query})
    assert resp.status == 200
    result = await resp.json()
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(string="nm", float=3.0),
                display=dict(choices=["m", "mm", "um", "nm"]),
            )
        )
    )


@pytest.mark.asyncio
async def test_put_long_and_enum(ioc: Popen, client, long_and_enum_put):
    query = long_and_enum_put
    resp = await client.post("/ws", json={"query": query})
    assert resp.status == 200
    result = await resp.json()
    assert result == dict(
        data=dict(
            putChannels=[
                dict(value=dict(string="55"), time=ANY),
                dict(value=dict(string="mm"), time=ANY),
            ]
        )
    )
    thens = [
        datetime.fromisoformat(r["time"]["datetime"])
        for r in result["data"]["putChannels"]
    ]
    now = datetime.now()
    for then in thens:
        diff = now - then
        # Shouldn't take more than this time to get the result of a put out
        assert diff.total_seconds() < 0.2


@pytest.mark.asyncio
async def test_put_list(ioc: Popen, client, list_put):
    query = list_put
    resp = await client.post("/ws", json={"query": query})
    assert resp.status == 200
    result = await resp.json()
    assert result == dict(
        data=dict(
            putChannels=[
                dict(
                    value=dict(
                        stringArray=["0.0", "1.7", "2.0"], base64Array=BASE64_0_1688_2
                    )
                )
            ]
        )
    )


@pytest.mark.asyncio
async def test_put_base64(ioc: Popen, client, base64_put):
    # first dump gives {"key": "value"}, a json string
    # second dump gives \{\"key\": \"value\"\}, an escaped json string
    query = base64_put
    resp = await client.post("/ws", json={"query": query})
    assert resp.status == 200
    result = await resp.json()
    assert result == dict(
        data=dict(putChannels=[dict(value=dict(stringArray=["0.0", "1.7", "2.0"]))])
    )


@pytest.mark.asyncio
async def test_subscribe_ticking_graphql_transport_ws_protocol(
    ioc: Popen, client, ticking_subscribe
):
    query = ticking_subscribe
    results = []
    await caput(PV_PREFIX + "ticking", 0.0)
    start = time.time()
    async with client.ws_connect(
        "/ws", protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL]
    ) as ws:
        await ws.send_json(ConnectionInitMessage().as_dict())

        response = await ws.receive_json()
        assert response == ConnectionAckMessage().as_dict()

        await ws.send_json(
            SubscribeMessage(
                id="sub1",
                payload=SubscribeMessagePayload(query=query),
            ).as_dict()
        )
        while True:
            if time.time() - start > 0.5:
                break
            result = await ws.receive_json()
            results.append(result["payload"])
        for i in range(3):
            display = None
            if i == 0:
                display = dict(precision=5, units="mm")
            assert results[i] == dict(
                data=dict(
                    subscribeChannel=dict(
                        value=dict(string="%.5f mm" % i), display=display
                    )
                )
            )
        assert len(results) == 3

        await ws.close()
        assert ws.closed


@pytest.mark.asyncio
async def test_subscribe_ticking_graphql_ws_protocol(
    ioc: Popen, client, ticking_subscribe
):
    query = ticking_subscribe
    results = []
    await caput(PV_PREFIX + "ticking", 0.0)
    start = time.time()
    async with client.ws_connect("/ws", protocols=[GRAPHQL_WS_PROTOCOL]) as ws:
        await ws.send_json(OperationMessage(type=GQL_CONNECTION_INIT))

        response = await ws.receive_json()
        assert response == OperationMessage(type=GQL_CONNECTION_ACK)

        await ws.send_json(
            OperationMessage(
                type=GQL_START,
                id="sub1",
                payload=StartPayload(query=query),
            )
        )
        while True:
            if time.time() - start > 0.5:
                break
            result = await ws.receive_json()
            # Ignore keep alive messages
            if result["type"] == GQL_CONNECTION_KEEP_ALIVE:
                continue
            results.append(result["payload"])
        for i in range(3):
            display = None
            if i == 0:
                display = dict(precision=5, units="mm")
            assert results[i] == dict(
                data=dict(
                    subscribeChannel=dict(
                        value=dict(string="%.5f mm" % i), display=display
                    )
                )
            )
        assert len(results) == 3

        await ws.close()
        assert ws.closed


# !! Must be the last test as it calls a disconnect
@pytest.mark.asyncio
async def test_subscribe_disconnect(ioc: Popen, client, longout_subscribe):
    query = longout_subscribe
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
                results.append(result["payload"])
                ioc.communicate("exit()")
            else:
                # Second response; done.
                results.append(result["payload"])
                break

        assert len(results) == 2
        assert results[0] == dict(
            data=dict(
                subscribeChannel=dict(
                    value=dict(float=55), status=dict(quality="VALID")
                )
            )
        )
        assert results[1] == dict(
            data=dict(subscribeChannel=dict(value=None, status=dict(quality="INVALID")))
        )

        await ws.close()
        assert ws.closed
