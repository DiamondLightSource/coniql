import asyncio

from aiohttp import web
from graphql import graphql
import graphql_ws
from graphql_ws.aiohttp import AiohttpConnectionContext

from coniql.schema import schema
from coniql.template import render_graphiql


async def get_query(request):
    content_type = request.content_type
    if content_type == 'application/graphql':
        return await request.text()
    elif content_type == 'application/json':
        return (await request.json())['query']


async def graphql_view(request):
    query = await get_query(request)
    result = await graphql(schema, query)
    errors = result.errors
    if errors:
        errors = [error.formatted for error in errors]
        result = {'errors': errors}
    else:
        result = {'data': result.data}
    return web.json_response(result)


async def graphiql_view(request):
    return web.Response(text=render_graphiql(), headers={'Content-Type': 'text/html'})


async def handle_subscriptions(request):
    wsr = web.WebSocketResponse(protocols=(graphql_ws.WS_PROTOCOL,))
    request.app["websockets"].add(wsr)
    await wsr.prepare(request)
    await request.app["subscription_server"].handle(wsr, None)
    request.app["websockets"].remove(wsr)
    return wsr


app = web.Application()
app.router.add_get('/subscriptions', handle_subscriptions)
app.router.add_get('/graphiql', graphiql_view)
app.router.add_get('/graphql', graphql_view)
app.router.add_post('/graphql', graphql_view)
app["subscription_server"] = graphql_ws.SubscriptionServer(
    schema, AiohttpConnectionContext
)
app["websockets"] = set()

async def on_shutdown(app):
    await asyncio.wait([wsr.close() for wsr in app["websockets"]])

app.on_shutdown.append(on_shutdown)

web.run_app(app, port=8000)
