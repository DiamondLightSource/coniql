from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict

import aiohttp_cors
import strawberry
from aiohttp import web
from strawberry.aiohttp.views import GraphQLView
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL

import coniql.strawberry_schema as schema
from coniql.caplugin import CAPlugin
from coniql.plugin import PluginStore
from coniql.pvaplugin import PVAPlugin
from coniql.simplugin import SimPlugin

from . import __version__


def make_context() -> Dict[str, Any]:
    store = PluginStore()
    store.add_plugin("ssim", SimPlugin())
    store.add_plugin("pva", PVAPlugin())
    store.add_plugin("ca", CAPlugin(), set_default=True)
    context = dict(store=store)
    return context


context = make_context()


class MyGraphQLView(GraphQLView):
    async def get_context(self, request: web.Request, response: web.StreamResponse):
        ctx = context
        return {"request": request, "response": response, "ctx": ctx}


def main(args=None) -> None:
    """
    Entry point of the application.
    """
    parser = ArgumentParser(description="CONtrol system Interface over graphQL")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "config_paths",
        metavar="PATH",
        type=Path,
        nargs="*",
        help="Paths to .coniql.yaml files describing Channels and Devices",
    )
    parser.add_argument(
        "--cors", action="store_true", help="Allow CORS for all origins and routes"
    )
    parsed_args = parser.parse_args(args)

    strawberry_schema = strawberry.Schema(
        query=schema.Query, subscription=schema.Subscription, mutation=schema.Mutation
    )

    view = MyGraphQLView(
        schema=strawberry_schema,
        subscription_protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL],
    )

    app = web.Application()

    app.router.add_route("GET", "/ws", view)
    app.router.add_route("POST", "/graphql", view)

    if parsed_args.cors:
        # Enable CORS for all origins on all routes.
        cors = aiohttp_cors.setup(app)
        for route in app.router.routes():
            allow_all = {
                "*": aiohttp_cors.ResourceOptions(
                    allow_headers=("*"), max_age=3600, allow_credentials=True
                )
            }
            cors.add(route, allow_all)

    web.run_app(app)
