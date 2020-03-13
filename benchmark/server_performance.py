import asyncio
import time
from typing import Optional, List
import base64

import numpy as np
from aiohttp import web
from graphql import graphql
import graphql_ws_next
from graphql_ws_next.aiohttp import AiohttpConnectionContext
from aiohttp import web

from coniql.schema import ConiqlSchema
from measure import print_request_times
from sim_sinewave import to_float_array


async def get_query(request):
    content_type = request.content_type
    if content_type == "application/graphql":
        return await request.text()
    elif content_type == "application/json":
        return (await request.json())["query"]


async def graphiql_view(request):
    return web.Response(text=render_graphiql(), headers={"Content-Type": "text/html"})


class App(web.Application):
    def __init__(self):
        super(App, self).__init__()
        self.router.add_get("/subscriptions", self.handle_subscriptions)
        self.router.add_get("/graphql", self.graphql_view)
        self.router.add_post("/graphql", self.graphql_view)
        self.websockets = set()
        self.schema = ConiqlSchema()
        from coniql.simplugin import SimPlugin

        self.schema.add_plugin("sim", SimPlugin())
        self.subscription_server = graphql_ws_next.SubscriptionServer(
            self.schema, AiohttpConnectionContext
        )
        self.on_startup.append(self.schema.startup)
        self.on_shutdown.append(self.schema.shutdown)
        self.on_shutdown.append(self.close_websockets)

    async def graphql_view(self, request):
        query = await get_query(request)
        result = await graphql(self.schema, query)
        errors = result.errors
        if errors:
            for error in errors:
                traceback.print_tb(error.__traceback__)
            errors = [error.formatted for error in errors]
            result = {"errors": errors}
        else:
            result = {"data": result.data}
        return web.json_response(result)

    async def handle_subscriptions(self, request):
        wsr = web.WebSocketResponse(protocols=(graphql_ws_next.WS_PROTOCOL,))
        self.websockets.add(wsr)
        await wsr.prepare(request)
        await self.subscription_server.handle(wsr, None)
        self.websockets.remove(wsr)
        return wsr

    async def close_websockets(self, _):
        if self.websockets:
            await asyncio.wait([wsr.close() for wsr in self.websockets])


async def measure_query_response(
    app: App, query: str, repeats: int = 100, label: Optional[str] = None
):
    request_times = []
    for request_num in range(repeats):
        start_time = time.time()
        result = await graphql(app.schema, query)
        end_time = time.time()
        request_times.append((end_time - start_time) * 1000)

    print_request_times(request_times, label)


async def measure_sinewave_query_response(
    app: App, size: int, repeats: int = 100, label: Optional[str] = None
):
    def validate_from_json(data: dict, expected: List[float]) -> bool:
        encoded_numbers = data["getChannel"]["value"]["base64"]
        number_array = to_float_array(encoded_numbers)
        return set(number_array) == set(expected)

    query = f"""query {{
  getChannel(id: "sim://sinewavesimple:{size}") {{
    value
  }}
}}
"""

    expected_values = [x for x in range(size)]

    request_times = []
    for request_num in range(repeats):
        start_time = time.time()
        result = await graphql(app.schema, query)
        end_time = time.time()
        # assert validate_from_json(result[0], expected_values)
        request_times.append((end_time - start_time) * 1000)

    print_request_times(request_times, label)


if __name__ == "__main__":

    sine_query_value_only = """
query {
  getChannel(id: "sim://sine") {
    value
  }
}
"""

    app = App()

    asyncio.run(
        measure_query_response(
            app, sine_query_value_only, repeats=1, label="Sine value"
        )
    )
    # asyncio.run(measure_sinewave_query_response(app, 1, label="Sine Wave of size 1"))
    # asyncio.run(measure_sinewave_query_response(app, 10, label="Sine Wave of size 10"))
    # asyncio.run(
    #     measure_sinewave_query_response(app, 100, label="Sine Wave of size 100")
    # )
    # asyncio.run(
    #     measure_sinewave_query_response(app, 1000, label="Sine Wave of size 1000")
    # )
    # asyncio.run(
    #     measure_sinewave_query_response(app, 10000, label="Sine Wave of size 10000")
    # )
    # asyncio.run(
    #     measure_sinewave_query_response(app, 100000, label="Sine Wave of size 100000")
    # )
    # asyncio.run(
    #     measure_sinewave_query_response(app, 1000000, label="Sine Wave of size 1000000")
    # )
    # asyncio.run(
    #     measure_sinewave_query_response(
    #         app, 10000000, label="Sine Wave of size 10000000"
    #     )
    # )
