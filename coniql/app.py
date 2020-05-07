import traceback
from pathlib import Path
from typing import Any, Dict

from aiohttp import web
from tartiflette import Engine, TartifletteError
from tartiflette_aiohttp import register_graphql_handlers

from coniql.plugin import PluginStore
from coniql.simplugin import SimPlugin


async def error_coercer(exception: Exception, error: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(exception, TartifletteError):
        e = exception.original_error
    else:
        e = exception
    traceback.print_exception(type(e), e, e.__traceback__)
    return error


def make_engine() -> Engine:
    engine = Engine(
        sdl=Path(__file__).resolve().parent / "schema.gql",
        error_coercer=error_coercer,
        modules=["coniql.resolvers"],
    )
    return engine


def make_context() -> Dict[str, Any]:
    plugins = PluginStore()
    plugins.add_plugin("sim", SimPlugin())
    return dict(plugins=plugins)


def run() -> None:
    """
    Entry point of the application.
    """
    web.run_app(
        register_graphql_handlers(
            app=web.Application(),
            executor_context=make_context(),
            executor_http_endpoint="/graphql",
            subscription_ws_endpoint="/ws",
            graphiql_enabled=True,
            engine=make_engine(),
        )
    )
