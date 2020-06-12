import pytest

from coniql.app import make_engine


@pytest.fixture(scope="session")
async def engine():
    engine = make_engine()
    await engine.cook()
    yield engine
