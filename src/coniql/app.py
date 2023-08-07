import logging
from argparse import ArgumentParser
from datetime import timedelta
from typing import Any, Optional

import aiohttp_cors
from aiohttp import web
from aiohttp.hdrs import METH_GET, METH_POST
from strawberry.aiohttp.views import GraphQLView
from strawberry.schema.config import StrawberryConfig
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL

import coniql.strawberry_schema as schema
from coniql.metrics import (
    MetricsExtension,
    MetricsGraphQLTransportWSHandler,
    MetricsGraphQLWSHandler,
    MetricsSchema,
    handle_metrics,
    metrics_middleware,
)

from . import __version__


def create_schema(debug: bool):
    # Disabling automatic camel casing saves ~1% CPU time as Strawberry won't attempt
    # to check/change our field names. Currently we don't have any snake_case fields
    # so there isn't any transformation happening anyway.
    config = StrawberryConfig(auto_camel_case=False)

    # Create the schema
    return MetricsSchema(
        query=schema.Query,
        subscription=schema.Subscription,
        mutation=schema.Mutation,
        extensions=[MetricsExtension],
        config=config,
    )


class GraphQLViewExtension(GraphQLView):
    """Use custom handlers to enable inprogress metrics for subscriptions"""

    graphql_transport_ws_handler_class = MetricsGraphQLTransportWSHandler
    graphql_ws_handler_class = MetricsGraphQLWSHandler


def create_app(
    use_cors: bool,
    debug: bool,
    graphiql: bool,
    connection_init_wait_timeout: Optional[timedelta] = None,
):
    # Create the schema
    strawberry_schema = create_schema(debug)

    kwargs: Any = {}
    if connection_init_wait_timeout:
        kwargs["connection_init_wait_timeout"] = connection_init_wait_timeout

    # Create the GraphQL view to attach to the app
    view = GraphQLViewExtension(
        schema=strawberry_schema,
        subscription_protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL],
        graphiql=graphiql,
        **kwargs,
    )

    # Create app
    app = web.Application(middlewares=[metrics_middleware])

    # Add routes
    app.router.add_route(METH_GET, "/ws", view)
    app.router.add_route(METH_POST, "/ws", view)
    app.router.add_route(METH_POST, "/graphql", view)

    app.router.add_route(METH_GET, "/metrics", handle_metrics)

    # Enable CORS for all origins on all routes (if applicable)
    if use_cors:
        cors = aiohttp_cors.setup(app)
        for route in app.router.routes():
            allow_all = {
                "*": aiohttp_cors.ResourceOptions(
                    allow_headers=("*"), max_age=3600, allow_credentials=True
                )
            }
            cors.add(route, allow_all)

    return app


def configure_logger(debug: bool = False, fmt: Optional[str] = None) -> None:
    class OptionalTraceFormatter(logging.Formatter):
        def __init__(self, debug: bool = False, fmt: Optional[str] = None) -> None:
            self.debug = debug
            super().__init__(fmt)

        def formatStack(self, stack_info: str) -> str:
            """Option to suppress the stack trace output"""
            if not self.debug:
                return ""
            return super().formatStack(stack_info)

    # Handler to print to stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if debug else logging.ERROR)
    console.setFormatter(OptionalTraceFormatter(debug, fmt))

    # Attach it to both Coniql and Strawberry loggers
    strawberry_logger = logging.getLogger("strawberry")
    strawberry_logger.addHandler(console)
    coniql_logger = logging.getLogger("coniql")
    coniql_logger.addHandler(console)


def main(args=None) -> None:
    """
    Entry point of the application.
    """
    parser = ArgumentParser(description="CONtrol system Interface over graphQL")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--cors",
        action="store_true",
        default=False,
        help="Allow CORS for all origins and routes",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Print stack trace on errors",
    )
    parser.add_argument(
        "--graphiql",
        action="store_true",
        default=False,
        help="Enable GraphiQL for testing at localhost:8080/ws",
    )
    parsed_args = parser.parse_args(args)

    logger_fmt = "[%(asctime)s::%(name)s::%(levelname)s]: %(message)s"
    configure_logger(parsed_args.debug, logger_fmt)

    app = create_app(parsed_args.cors, parsed_args.debug, parsed_args.graphiql)
    web.run_app(app)
