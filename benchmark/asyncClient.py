"""
Notes taken from py-graphql-client

Connection initial message:
{'payload': {'headers': None}, 'type': 'connection_init'}

Response from server:
{'type': 'connection_ack'}

Subscription request:
{
    'id': 'e2eff452fe9f4533a0f...bf7a07153',
    'payload':
        {
            'headers': None,
            'query': 'subscription {\n  s...n  }\n}\n',
            'variables': None
        },
    'type': 'start'
}

Possible resonse
'{"type": "connection_ack"}'

More useful response:
{
    'type': 'data',
    'id':'1131392b291a4f1a9a719a85d15130fb',
    "payload":
        {
            "data":
                {"subscribeChannel":
                    {"id": "sim://sinewavesimple(10000,0.1)",
                    "value":
                        {"numberType": "FLOAT64",
                        "base64": "A......A"

Stop message
{'id': '2a6970c41c994c37926...a713689c1', 'type': 'stop'}
"""

import asyncio
import base64
import json
import time
from typing import List, cast

import numpy as np
from websockets.client import connect
from websockets.typing import Subprotocol

GQL_WS_SUBPROTOCOL = "graphql-ws"

# all the message types
GQL_CONNECTION_INIT = "connection_init"
GQL_START = "start"
GQL_STOP = "stop"
GQL_CONNECTION_TERMINATE = "connection_terminate"
GQL_CONNECTION_ERROR = "connection_error"
GQL_CONNECTION_ACK = "connection_ack"
GQL_DATA = "data"
GQL_ERROR = "error"
GQL_COMPLETE = "complete"
GQL_CONNECTION_KEEP_ALIVE = "ka"


TEST_SUBSCRIPTION_URL = "ws://localhost:8080/ws"


def to_float_array(input_data: str) -> List[float]:
    return np.frombuffer(
        base64.decodebytes(input_data.encode("ascii")), dtype=np.float64
    )


async def subscribe(size: int, update_time: float, messages_to_test: int) -> float:
    async with connect(
        TEST_SUBSCRIPTION_URL,
        subprotocols=[cast(Subprotocol, GQL_WS_SUBPROTOCOL)],
        max_size=2**40,
        compression=None,
    ) as ws:
        print("--- ssim://sinewavesimple ---")
        print(
            f"--- Size: {size}, Update Time: {update_time} s, \
            Messages to test: {messages_to_test}, ---"
        )

        # matching_numbers = np.array([x for x in range(size)], dtype=np.float64)

        await ws.send(
            json.dumps({"payload": {"headers": None}, "type": "connection_init"})
        )
        await ws.recv()
        print("Connected...")

        channel = f"ssim://rampwave({size},{update_time})"
        await ws.send(
            json.dumps(
                {
                    "id": "e2eff452fe9f4533a0fbf7a07153",
                    "payload": {
                        "headers": None,
                        "query": """
                            subscription {
                                subscribeChannel(id: "%s") {
                                    id
                                    value {
                                        base64Array {
                                            numberType
                                            base64
                                        }
                                    }
                                }
                            }
                        """
                        % channel,
                        "variables": None,
                    },
                    "type": "start",
                }
            )
        )

        start_time = time.time()
        for i in range(messages_to_test):
            await ws.recv()
            # # res = await ws.recv()
            # # loaded = json.loads(res)
            # try:
            #     encoded_numbers = json.loads(await ws.recv())["payload"]["data"][
            #         "subscribeChannel"
            #     ]["value"]["base64Array"]["base64"]
            #     # assert encoded_numbers
            #     assert np.array_equal(matching_numbers, \
            #        to_float_array(encoded_numbers))
            #     matching_numbers = np.roll(matching_numbers, 1)
            # except AssertionError:
            #     print(f"Expected a set of numbers from 0 to {size} \
            #        but did not recieve")
            #     matching_numbers = to_float_array(encoded_numbers)
            # except KeyError:
            #     print("Issue with incoming data")
            # print("recvd...")
        end_time = time.time()
    print(f"Time taken: {end_time - start_time:2f} s")
    print(f"Frequency: {100 / (end_time - start_time):3f} Hz")
    return 100 / (end_time - start_time)


async def test_sizes():
    results = []
    results.append(await subscribe(100000, 0.1, 100))
    results.append(await subscribe(200000, 0.1, 100))
    results.append(await subscribe(300000, 0.1, 100))
    results.append(await subscribe(400000, 0.1, 100))
    results.append(await subscribe(500000, 0.1, 100))
    results.append(await subscribe(600000, 0.1, 100))
    results.append(await subscribe(700000, 0.1, 100))
    results.append(await subscribe(800000, 0.1, 100))
    results.append(await subscribe(900000, 0.1, 100))
    results.append(await subscribe(1000000, 0.1, 100))
    results.append(await subscribe(2000000, 0.1, 100))
    results.append(await subscribe(3000000, 0.1, 100))
    results.append(await subscribe(4000000, 0.1, 100))
    results.append(await subscribe(5000000, 0.1, 100))

    for r in results:
        print(r)


asyncio.get_event_loop().run_until_complete(test_sizes())
