import traceback
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict

from aiohttp import web
from tartiflette import Engine, TartifletteError
from tartiflette_aiohttp import register_graphql_handlers

from coniql.device_config import ConfigStore, DeviceConfig
from coniql.plugin import PluginStore
from coniql.simplugin import SimPlugin


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
    plugins = PluginStore()
    plugins.add_plugin("sim", SimPlugin())
    configs = ConfigStore()
    for path in schema_paths:
        device_config = DeviceConfig.from_yaml(path)
        configs.add_device_config(device_config)
    context = dict(plugins=plugins, configs=configs)
    return context


def main(args=None) -> None:
    """
    Entry point of the application.
    """
    parser = ArgumentParser(description="CONtrol system Interface over graphQL")
    parser.add_argument(
        "config_paths",
        metavar="PATH",
        type=Path,
        nargs="+",
        help="Paths to .coniql.yaml files describing Channels and Devices",
    )
    parsed_args = parser.parse_args(args)

    web.run_app(
        register_graphql_handlers(
            app=web.Application(),
            executor_context=make_context(*parsed_args.config_paths),
            executor_http_endpoint="/graphql",
            subscription_ws_endpoint="/ws",
            graphiql_enabled=True,
            engine=make_engine(),
        )
    )
