from typing import Dict, List, Optional

from aioca import Subscription
from aioca._catools import _Context
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
    timer,
)
from aioprometheus.asgi.middleware import EXCLUDE_PATHS
from aioprometheus.renderer import render
from graphql import GraphQLError
from strawberry.aiohttp.handlers import GraphQLTransportWSHandler, GraphQLWSHandler
from strawberry.extensions import SchemaExtension
from strawberry.schema import Schema
from strawberry.types import ExecutionContext

# Create all the metrics for the entire application here
# TODO: const labels?
REQUESTS_IN_PROGRESS = Gauge(
    "coniql_request_in_progress", "Number of requests in progress"
)
REQUEST_TIME = Summary(
    "coniql_request_processing_seconds", "Time spent processing request"
)
REQUESTS = Counter("coniql_request_total", "Total number of requests")
REQUEST_EXCEPTIONS = Counter(
    "coniql_request_handler_exceptions", "Number of exceptions in requests"
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


class SchemaWithMetrics(Schema):
    """Extended Schema with metrics"""

    def process_errors(
        self,
        errors: List[GraphQLError],
        execution_context: Optional[ExecutionContext] = None,
    ):
        """Override to count the number of GraphQL errors"""
        labels = {"route": "GraphQL"}
        for _ in range(len(errors)):
            if (
                execution_context
                and execution_context.context
                and "request" in execution_context.context
            ):
                # TODO: different label per error? Otherwise we could increment
                # multiple times
                labels.update({"remote": execution_context.context["request"].remote})

            REQUEST_EXCEPTIONS.inc(labels)

        super().process_errors(errors, execution_context)


class MetricsGraphQLTransportWSHandler(GraphQLTransportWSHandler):
    """Custom override of GraphQLTransportWSHandler to allow adding the @inprogress
    annotation. Tracks how many subscriptions are currently active."""

    @inprogress(
        REQUESTS_IN_PROGRESS, labels={"type": "subscription_GraphQLTransportWS"}
    )
    async def handle_request(self):
        await super().handle_request()


class MetricsGraphQLWSHandler(GraphQLWSHandler):
    """Custom override of GraphQLWSHandler to allow adding the @inprogress
    annotation. Tracks how many subscriptions are currently active."""

    @inprogress(REQUESTS_IN_PROGRESS, labels={"type": "subscription_GraphQLWS"})
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

    # Avoid adding 0 as that causes the metric+labels to be published
    if difference:
        DROPPED_UPDATES.add(labels, difference)
    return current_dropped_count


def update_active_channels() -> None:
    """Inspect aioca's channel cache to see how many active channels there are"""
    channel_cache = _Context.get_channel_cache()
    ACTIVE_CHANNELS.set({}, len(channel_cache._ChannelCache__channels))


async def handle_metrics(request: Request):
    """Create the output for all defined metrics, in a format determined by the
    request's ACCEPT headers."""
    update_active_channels()
    content, http_headers = render(REGISTRY, request.headers.getall(ACCEPT, []))
    return web.Response(body=content, headers=http_headers)


@web.middleware
# TODO: The below timer also tracks the response time of the /metrics endpoint itself...
@timer(REQUEST_TIME)  # Keeps track of duration of all requests
@count_exceptions(
    REQUEST_EXCEPTIONS, {"route": "middleware"}
)  # Count any exceptions in any request
async def metrics_middleware(request: Request, handler):
    """Middleware that is called for all requests to the aiohttp server"""

    # Ignore requests for some common paths.
    # Use the same list as used in aioprometheus for AGSI apps
    if request.path not in EXCLUDE_PATHS:
        REQUESTS.inc({"route": "middleware ", "path": request.path})

    response = await handler(request)

    # TODO: Work out how to ignore e.g. HTTP 404 errors on favicon as there just
    # isn't one
    # Probably hold off until:
    # - Get newest favicon from Becky (maybe)
    # - Wait until Andy has ported to newest skeleton

    return response
