import time
from typing import Dict, List, Optional

from aioca import Subscription, get_channel_infos
from aiohttp import web
from aiohttp.hdrs import ACCEPT
from aiohttp.web_request import Request
from aioprometheus import (
    REGISTRY,
    Counter,
    Gauge,
    Summary,
    count_exceptions,
    inprogress,
)
from aioprometheus.asgi.middleware import EXCLUDE_PATHS
from aioprometheus.renderer import render
from graphql import GraphQLError
from strawberry.aiohttp.handlers import GraphQLTransportWSHandler, GraphQLWSHandler
from strawberry.extensions import SchemaExtension
from strawberry.schema import Schema
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL
from strawberry.types import ExecutionContext

# Create all the metrics for the entire application here
SUBSCRIPTIONS_IN_PROGRESS = Gauge(
    "coniql_subscriptions_in_progress", "Number of subscriptions in progress"
)
REQUEST_TIME = Summary(
    "coniql_request_processing_seconds", "Time spent processing request"
)
REQUESTS = Counter("coniql_request_total", "Total number of requests")
REQUEST_EXCEPTIONS = Counter(
    "coniql_request_handler_exceptions",
    "Number of exceptions and GraphQL errors in requests",
)
DROPPED_UPDATES = Gauge(
    "coniql_dropped_updates", "Number of updates dropped in subscriptions"
)
ACTIVE_CHANNELS = Gauge("coniql_active_channels", "Number of active channels in aioca")


class MetricsExtension(SchemaExtension):
    def on_operation(self):
        """Counts the number of GraphQL Queries and Mutations"""
        REQUESTS.inc({"route": "GraphQL"})
        yield


class MetricsSchema(Schema):
    """Extended Schema with metrics"""

    def process_errors(
        self,
        errors: List[GraphQLError],
        execution_context: Optional[ExecutionContext] = None,
    ):
        """Override to count the number of GraphQL errors"""
        labels = {"route": "GraphQL"}
        # Technically there could be multiple GraphQL errors present, but for metric
        # purposes we really only care that any happened.
        if len(errors):
            if (
                execution_context
                and execution_context.context
                and "request" in execution_context.context
            ):
                # If we can, add the remote end's address
                labels.update({"remote": execution_context.context["request"].remote})
            REQUEST_EXCEPTIONS.inc(labels)

        super().process_errors(errors, execution_context)


class MetricsGraphQLTransportWSHandler(GraphQLTransportWSHandler):
    """Custom override of GraphQLTransportWSHandler to allow adding the @inprogress
    annotation. Tracks how many subscriptions are currently active."""

    @inprogress(
        SUBSCRIPTIONS_IN_PROGRESS,
        labels={"type": f"subscription_{GRAPHQL_TRANSPORT_WS_PROTOCOL}"},
    )
    async def handle_request(self):
        await super().handle_request()


class MetricsGraphQLWSHandler(GraphQLWSHandler):
    """Custom override of GraphQLWSHandler to allow adding the @inprogress
    annotation. Tracks how many subscriptions are currently active."""

    @inprogress(
        SUBSCRIPTIONS_IN_PROGRESS,
        labels={"type": f"subscription_{GRAPHQL_WS_PROTOCOL}"},
    )
    async def handle_request(self):
        await super().handle_request()


def update_subscription_metrics(
    subscription: Subscription, last_dropped_count: int, labels: Dict[str, str]
) -> int:
    """Inspect the given Subscription to update the relevant metrics.
    Must provide the number of dropped updates prevously observed.
    Returns the current number of dropped updates."""
    labels.update({"pv": subscription.name})
    # Ensure only read dropped_callbacks once, in case it is updating in the background
    current_dropped_count = subscription.dropped_callbacks

    difference = current_dropped_count - last_dropped_count

    # Note that adding 0 will still cause the metric to be published
    DROPPED_UPDATES.add(labels, difference)
    return current_dropped_count


def update_active_channels() -> None:
    """Inspect aioca's channel cache to see how many active channels there are"""
    channel_infos = get_channel_infos()

    active_channels = sum(channel.connected for channel in channel_infos)

    ACTIVE_CHANNELS.set({}, active_channels)


async def handle_metrics(request: Request):
    """Create the output for all defined metrics, in a format determined by the
    request's ACCEPT headers."""
    update_active_channels()
    content, http_headers = render(REGISTRY, request.headers.getall(ACCEPT, []))
    return web.Response(body=content, headers=http_headers)


@web.middleware
@count_exceptions(
    REQUEST_EXCEPTIONS, {"route": "middleware"}
)  # Count any exceptions in any request
async def metrics_middleware(request: Request, handler):
    """Middleware that is called for all requests to the aiohttp server"""

    labels = {"route": "middleware", "path": request.path}

    # Ignore requests for some common paths.
    # Use the same list as used in aioprometheus for AGSI apps
    if request.path not in EXCLUDE_PATHS:
        REQUESTS.inc(labels)
        start_time = time.monotonic()

    response = await handler(request)

    if request.path not in EXCLUDE_PATHS:
        REQUEST_TIME.observe(labels, time.monotonic() - start_time)

    return response
