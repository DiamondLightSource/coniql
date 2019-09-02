#!/bin/env python
import asyncio
import traceback
from pathlib import Path
from typing import Dict

from aiohttp import web
from graphql import graphql, build_schema
import graphql_ws_next
from coniql.plugin import Plugin
from graphql_ws_next.aiohttp import AiohttpConnectionContext

from coniql.pvaplugin import PVAPlugin
from coniql.template import render_graphiql


DB = Path(__file__).parent / "database.db"
SCHEMA = Path(__file__).parent / "schema.graphql"


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
        self.plugins: Dict[str, Plugin] = dict(pva=PVAPlugin())
        self.plugins[""] = self.plugins["pva"]
        with open(SCHEMA) as f:
            self.schema = build_schema(f.read())
        self.schema.query_type.fields["getChannel"].resolve = \
            self.get_channel
        self.schema.mutation_type.fields["putChannel"].resolve = \
            self.put_channel
        self.schema.subscription_type.fields["subscribeChannel"].subscribe = \
            self.subscribe_channel
        self.subscription_server = graphql_ws_next.SubscriptionServer(
            self.schema, AiohttpConnectionContext
        )
        self.on_startup.append(start_ioc)
        self.on_shutdown.append(self.do_shutdown)

    def plugin_channel(self, id: str):
        split = id.split("://", 1)
        if len(split) == 1:
            scheme, channel_id = "", id
        else:
            scheme, channel_id = split
        try:
            plugin = self.plugins[scheme]
        except KeyError:
            raise ValueError("No plugin registered for scheme '%s'" % scheme)
        return plugin, channel_id

    async def get_channel(self, root, info, id: str, timeout: float):
        plugin, channel_id = self.plugin_channel(id)
        data = await plugin.get_channel(channel_id, timeout)
        data["id"] = id
        return data

    async def put_channel(self, root, info, id: str, value, timeout: float):
        plugin, channel_id = self.plugin_channel(id)
        data = await plugin.put_channel(channel_id, value, timeout)
        return data

    async def subscribe_channel(self, root, info, id: str):
        try:
            plugin, channel_id = self.plugin_channel(id)
            async for data in plugin.subscribe_channel(channel_id):
                data["id"] = id
                yield dict(subscribeChannel=data)
        except Exception as e:
            # TODO: I'm sure it's possible to raise an exception from a subscription...
            message = "%s: %s" % (e.__class__.__name__, e)
            d = dict(subscribeChannel=dict(id=id, status=dict(
                quality="ALARM", message=message, mutable=False)))
            yield d
            traceback.print_exc()
            raise

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
        for plugin in set(self.plugins.values()):
            plugin.destroy()
        self.plugins = None


web.run_app(App(), port=8000)
