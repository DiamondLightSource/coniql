#!/bin/env python
import asyncio
from pathlib import Path

from aiohttp import web
from graphql import graphql
import graphql_ws_next
from graphql_ws_next.aiohttp import AiohttpConnectionContext

from coniql.pvaplugin import PVAPlugin
# from coniql.simplugin import SimPlugin
from coniql.template import render_graphiql
from coniql.schema import ConiqlSchema


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
        self.websockets = set()
        self.schema = ConiqlSchema()
        self.schema.add_plugin("pva", PVAPlugin(), set_default=True)
        self.subscription_server = graphql_ws_next.SubscriptionServer(
            self.schema, AiohttpConnectionContext
        )
        self.on_startup.append(start_ioc)
        self.on_shutdown.append(self.do_shutdown)

    async def graphql_view(self, request):
        query = await get_query(request)
        result = await graphql(self.schema, query)
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
        await self.subscription_server.handle(wsr, None)
        self.websockets.remove(wsr)
        return wsr

    async def do_shutdown(self, _):
        if self.websockets:
            await asyncio.wait([wsr.close() for wsr in self.websockets])
        self.schema.destroy()


web.run_app(App(), port=8000)
