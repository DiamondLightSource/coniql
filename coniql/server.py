#!/bin/env python

import asyncio
from pathlib import Path

from aiohttp import web
from graphql import graphql
import graphql_ws_next
from graphql_ws_next.aiohttp import AiohttpConnectionContext
from p4p.client.asyncio import Context

from coniql.pvaschema import schema
from coniql.template import render_graphiql


DB = Path(__file__).parent / "database.db"


async def get_query(request):
    content_type = request.content_type
    if content_type == 'application/graphql':
        return await request.text()
    elif content_type == 'application/json':
        return (await request.json())['query']


async def graphiql_view(request):
    return web.Response(
        text=render_graphiql(), headers={'Content-Type': 'text/html'})


async def run_ioc():
    cmd = f'/scratch/base-7.0.2.2/bin/linux-x86_64/softIocPVA -d {DB}'
    print(f'{cmd!r}')
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')


async def start_ioc(app):
    app['ioc'] = asyncio.create_task(run_ioc())


class App(web.Application):
    def __init__(self):
        super(App, self).__init__()
        self.router.add_get('/subscriptions', self.handle_subscriptions)
        self.router.add_get('/graphiql', graphiql_view)
        self.router.add_get('/graphql', self.graphql_view)
        self.router.add_post('/graphql', self.graphql_view)
        self.subscription_server = graphql_ws_next.SubscriptionServer(
            schema, AiohttpConnectionContext
        )
        self.websockets = set()
        self.ctxt = Context("pva", unwrap={})
        self.on_startup.append(start_ioc)
        self.on_shutdown.append(self.close_all_websockets)
        self.on_shutdown.append(lambda _: self.ctxt.close())

    async def graphql_view(self, request):
        query = await get_query(request)
        result = await graphql(schema, query, context_value=self.ctxt)
        errors = result.errors
        if errors:
            errors = [error.formatted for error in errors]
            result = {'errors': errors}
        else:
            result = {'data': result.data}
        return web.json_response(result)

    async def handle_subscriptions(self, request):
        wsr = web.WebSocketResponse(protocols=(graphql_ws_next.WS_PROTOCOL,))
        self.websockets.add(wsr)
        await wsr.prepare(request)
        await self.subscription_server.handle(wsr, context_value=self.ctxt)
        self.websockets.remove(wsr)
        return wsr

    async def close_all_websockets(self, _):
        if self.websockets:
            await asyncio.wait([wsr.close() for wsr in self.websockets])


web.run_app(App(), port=8000)
