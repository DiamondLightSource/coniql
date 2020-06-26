import pytest

from coniql.app import make_engine

# Per session Engine, as tartiflette doesn't seem to like remaking them for the
# same schema
THE_ENGINE = make_engine()


# Would like to make this session scoped, but that plays badly with the function
# scoped event_loop. We want to keep a function scoped event loop, so cheat by
# returning a global engine in a function scoped fixture
@pytest.fixture()
async def engine():
    await THE_ENGINE.cook()  # schema_name=schema_name)
    yield THE_ENGINE
