import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Optional

import aiohttp_cors
import strawberry
from aiohttp import web
from graphql import GraphQLError
from strawberry.aiohttp.views import GraphQLView
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL
from strawberry.types import ExecutionContext

import coniql.strawberry_schema as schema

from . import __version__


class ConiqlSchema(strawberry.Schema):
    # Override to remove stack trace printer with every log
    def process_errors(
        self,
        errors: List[GraphQLError],
        execution_context: Optional[ExecutionContext] = None,
    ) -> None:
        for error in errors:
            if not error.message:
                logging.error("Unknown error occurred. Enable debugging to find cause.")
            else:
                logging.error(error.message)


def create_schema(debug: bool):
    # Create the schema
    if debug:
        return strawberry.Schema(
            query=schema.Query,
            subscription=schema.Subscription,
            mutation=schema.Mutation,
        )
    else:
        return ConiqlSchema(
            query=schema.Query,
            subscription=schema.Subscription,
            mutation=schema.Mutation,
        )


def create_app(use_cors: bool, debug: bool):
    # Create the schema
    strawberry_schema = create_schema(debug)

    # Create the GraphQL view to attach to the app
    view = GraphQLView(
        schema=strawberry_schema,
        subscription_protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL],
    )

    # Create app
    app = web.Application()
    # Add routes
    app.router.add_route("GET", "/ws", view)
    app.router.add_route("POST", "/ws", view)
    app.router.add_route("POST", "/graphql", view)
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
    parser.add_argument(
        "--debug", action="store_true", help="Print stack trace on errors"
    )
    parsed_args = parser.parse_args(args)

    debug = False
    if parsed_args.debug:
        debug = True

    cors = False
    if parsed_args.cors:
        cors = True

    app = create_app(cors, debug)
    web.run_app(app)
