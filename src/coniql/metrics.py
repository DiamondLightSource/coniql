from aiohttp import web
from aiohttp.hdrs import ACCEPT
from aiohttp.web_request import Request
from aioprometheus import REGISTRY, Counter, Gauge, Summary, inprogress, timer
from aioprometheus.renderer import render
from strawberry.aiohttp.handlers import GraphQLTransportWSHandler, GraphQLWSHandler
from strawberry.extensions import SchemaExtension

# Create all the metrics for the entire application here
# TODO: const labels?
REQUESTS_IN_PROGRESS = Gauge("request_in_progress", "Number of requests in progress")
REQUEST_TIME = Summary("request_processing_seconds", "Time spent processing request")
REQUESTS = Counter("request_total", "Total number of requests")


class MetricsExtension(SchemaExtension):
    def on_operation(self):
        """Counts the number of GraphQL Queries and Mutations"""
        REQUESTS.inc({"route": "GraphQL"})
        yield


async def handle_metrics(request: Request):
    """Create the HTML output for all defined metrics"""
    content, http_headers = render(REGISTRY, request.headers.getall(ACCEPT, []))
    return web.Response(body=content, headers=http_headers)


@web.middleware
@timer(REQUEST_TIME)  # Keeps track of duration of all requests
async def metrics_middleware(request: Request, handler):
    """Middleware that is called for all requests to the aiohttp server"""
    REQUESTS.inc({"route": "middleware ", "path": request.path})
    response = await handler(request)
    return response


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
