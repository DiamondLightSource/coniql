import importlib
from unittest.mock import MagicMock

import pytest
from aiohttp.test_utils import TestClient
from aioprometheus import REGISTRY

import coniql.app
import coniql.metrics
from coniql.metrics import (
    ACTIVE_CHANNELS,
    DROPPED_UPDATES,
    REQUEST_EXCEPTIONS,
    REQUEST_TIME,
    REQUESTS,
    SUBSCRIPTIONS_IN_PROGRESS,
    update_subscription_metrics,
)

from .conftest import enum_get_query, longout_get_query, nan_get_query


@pytest.fixture(autouse=True)
def clear_metrics():
    """Reset all metrics before and after each metrics-based test"""
    REGISTRY.clear()
    # Must forcibly reload the modules in order to a) recreate the metrics and
    # b) re-create the "metrics_middleware" wrapped function that is used when
    # creating the application.
    importlib.reload(coniql.metrics)
    importlib.reload(coniql.app)
    yield
    REGISTRY.clear()


@pytest.mark.asyncio
async def test_metrics_endpoint(client: TestClient):
    """Test the metrics endpoint starts and returns basic info"""

    resp = await client.get("/metrics")
    assert resp.status == 200

    text = await resp.text()
    expected_collectors = REGISTRY.collectors

    # Check the endpoint returns the same number of collectors as the registry
    assert text.count("HELP") == len(expected_collectors)
    assert text.count("TYPE") == len(expected_collectors)

    # And check that each named expected item exists
    assert ACTIVE_CHANNELS.name in text
    assert DROPPED_UPDATES.name in text
    assert REQUEST_EXCEPTIONS.name in text
    assert REQUEST_TIME.name in text
    assert REQUESTS.name in text
    assert SUBSCRIPTIONS_IN_PROGRESS.name in text


@pytest.mark.asyncio
async def test_metrics_query_count(ioc, client: TestClient):
    """Test metrics for counting GraphQL Queries and Mutations"""

    resp = await client.get("/ws", params={"query": longout_get_query})
    assert resp.status == 200

    resp = await client.get("/metrics")
    assert resp.status == 200

    text = await resp.text()

    # The request total metrics
    assert 'coniql_request_total{path="/ws",route="middleware"} 1' in text
    assert 'coniql_request_total{route="GraphQL"} 1' in text


@pytest.mark.asyncio
async def test_metrics_processing_time(ioc, client: TestClient):
    """Test metrics for duration of requests.
    Note that this will only count the first request (/ws), as that is the only
    completed request at the time the metrics output are created. There will be no
    timing information for the /metrics call itself."""

    resp = await client.get("/ws", params={"query": longout_get_query})
    assert resp.status == 200

    resp = await client.get("/metrics")
    assert resp.status == 200

    text = await resp.text()

    # Only expect 1 as the current request isn't tracked
    assert (
        "coniql_request_processing_seconds_count"
        '{path="/ws",route="middleware"} 1' in text
    )
    assert (
        "coniql_request_processing_seconds"
        '{path="/ws",quantile="0.5",route="middleware"}' in text
    )
    assert (
        "coniql_request_processing_seconds"
        '{path="/ws",quantile="0.9",route="middleware"}' in text
    )
    assert (
        "coniql_request_processing_seconds"
        '{path="/ws",quantile="0.99",route="middleware"}' in text
    )
    assert (
        "coniql_request_processing_seconds_sum"
        '{path="/ws",route="middleware"}' in text
    )


@pytest.mark.asyncio
async def test_metrics_active_channels(ioc, client: TestClient):
    """Test metrics for counting active channels in aioca"""

    # Open three Channels (three different PVs)
    resp = await client.get("/ws", params={"query": longout_get_query})
    assert resp.status == 200
    resp = await client.get("/ws", params={"query": enum_get_query})
    assert resp.status == 200
    resp = await client.get("/ws", params={"query": nan_get_query})
    assert resp.status == 200

    resp = await client.get("/metrics")
    assert resp.status == 200

    text = await resp.text()

    assert "coniql_active_channels 3" in text


@pytest.mark.asyncio
async def test_metrics_graphql_exception(client: TestClient):
    """Test metrics for counting GraphQL errors"""

    # Deliberately send a malformed query
    resp = await client.get("/ws", params={"query": longout_get_query[0:100]})
    assert resp.status == 200

    resp = await client.get("/metrics")
    assert resp.status == 200

    text = await resp.text()

    assert (
        'coniql_request_handler_exceptions{remote="127.0.0.1",route="GraphQL"} 1'
        in text
    )


@pytest.mark.asyncio
async def test_metrics_aiohttp_exception(client: TestClient):
    """Test metrics for counting aiohttp errors"""

    resp = await client.get("/fake_endpoint")
    assert resp.status == 404

    resp = await client.get("/metrics")
    assert resp.status == 200

    text = await resp.text()

    assert 'coniql_request_handler_exceptions{route="middleware"} 1' in text


@pytest.mark.asyncio
async def test_metrics_mocked_dropped_updates(client: TestClient):
    """Test metrics for dropped subscriptions by using mocked methods.
    This is done because it's very difficult to deliberately make aioca miss updates"""

    mocked_subscription = MagicMock()
    mocked_subscription.name = "TEST-NAME"
    mocked_subscription.dropped_callbacks = 5

    last_dropped = 0
    last_dropped = update_subscription_metrics(mocked_subscription, last_dropped, {})
    assert last_dropped == 5

    resp = await client.get("/metrics")
    assert resp.status == 200

    text = await resp.text()

    assert 'coniql_dropped_updates{pv="TEST-NAME"} 5' in text

    last_dropped = update_subscription_metrics(mocked_subscription, last_dropped, {})
    assert last_dropped == 5


@pytest.mark.asyncio
async def test_metrics_subscriptions_in_progress(
    ioc, client: TestClient, subscription_data
):
    """Test metrics for subscriptions in progress"""
    ws_protocol, msg_init, msg_ack, msg_send = subscription_data

    async with client.ws_connect("/ws", protocols=[ws_protocol]) as ws:
        await ws.send_json(msg_init)
        response = await ws.receive_json()
        assert response == msg_ack

        await ws.send_json(msg_send)

        resp = await client.get("/metrics")
        assert resp.status == 200

        text = await resp.text()
        assert (
            f'coniql_subscriptions_in_progress{{type="subscription_{ws_protocol}"}} 1'
            in text
        )

        await ws.close()
        assert ws.closed


@pytest.mark.asyncio
async def test_metrics_openmetrics_format(client: TestClient):
    """Test that the metrics endpoint can return data in openmetrics format, which
    is what Prometheus expects"""
    resp = await client.get(
        "/metrics", headers={"Accept": "application/openmetrics-text;version=1.0.0"}
    )
    assert resp.status == 200

    text = await resp.text()

    # Check an arbitrary line is in the right format
    assert "# TYPE coniql_active_channels gauge" in text
