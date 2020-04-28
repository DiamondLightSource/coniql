#!/bin/env python
import asyncio
import os
import traceback

from aiohttp import web
from graphql import graphql
import graphql_ws_next
from graphql_ws_next.aiohttp import AiohttpConnectionContext

from coniql import EPICS7_BASE
from coniql.template import render_graphiql
from coniql.schema import ConiqlSchema


async def get_query(request):
    content_type = request.content_type
    if content_type == 'application/graphql':
        return await request.text()
    elif content_type == 'application/json':
        return (await request.json())['query']


async def graphiql_view(request):
    return web.Response(
        text=render_graphiql(), headers={'Content-Type': 'text/html'})


class App(web.Application):
    def __init__(self):
        super(App, self).__init__()
        self.router.add_get('/subscriptions', self.handle_subscriptions)
        self.router.add_get('/graphiql', graphiql_view)
        self.router.add_get('/graphql', self.graphql_view)
        self.router.add_post('/graphql', self.graphql_view)
        self.websockets = set()
        self.schema = ConiqlSchema()
        if EPICS7_BASE in os.environ:
            from coniql.pvaplugin import PVAPlugin
            self.schema.add_plugin("pva", PVAPlugin(), set_default=True)
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
            result = {'errors': errors}
        else:
            result = {'data': result.data}
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


web.run_app(App(), port=8000)
