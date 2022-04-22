import traceback
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict

import aiohttp_cors
from aiohttp import web
from tartiflette import Engine, TartifletteError
from tartiflette_aiohttp import register_graphql_handlers

from coniql.caplugin import CAPlugin
from coniql.plugin import PluginStore
from coniql.pvaplugin import PVAPlugin
from coniql.simplugin import SimPlugin

from . import __version__


async def error_coercer(exception: Exception, error: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(exception, TartifletteError):
        e = exception.original_error
    else:
        e = exception
    if e:
        traceback.print_exception(type(e), e, e.__traceback__)
    return error


def make_engine() -> Engine:
    engine = Engine(
        sdl=Path(__file__).resolve().parent / "schema.gql",
        error_coercer=error_coercer,
        modules=["coniql.resolvers"],
    )
    return engine


def make_context(*schema_paths: Path) -> Dict[str, Any]:
    store = PluginStore()
    store.add_plugin("ssim", SimPlugin())
    store.add_plugin("pva", PVAPlugin())
    store.add_plugin("ca", CAPlugin(), set_default=True)
    for path in schema_paths:
        store.add_device_config(path)
    context = dict(store=store)
    return context


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

    context = make_context(*parsed_args.config_paths)
    app = register_graphql_handlers(
        app=web.Application(),
        executor_context=context,
        executor_http_endpoint="/graphql",
        subscription_ws_endpoint="/ws",
        graphiql_enabled=True,
        engine=make_engine(),
    )

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
