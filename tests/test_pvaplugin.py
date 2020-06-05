import pytest
from p4p.nt import NTEnum, NTScalar
from p4p.server import Server
from p4p.server.asyncio import SharedPV
from tartiflette import Engine

from coniql.app import make_context


@pytest.fixture(scope="module")
async def ioc():
    pv = SharedPV(
        nt=NTScalar("d", display=True, control=True, valueAlarm=True), initial=2.0
    )
    pv2 = SharedPV(nt=NTEnum(), initial=dict(index=1, choices=["ZERO", "ONE", "TWO"]))

    @pv.put
    def handle(pv, op):
        pv.post(op.value())  # just store and update subscribers
        op.done()

    s = Server(providers=[{"demo:float": pv, "demo:enum": pv2}])
    yield s
    s.stop()


@pytest.mark.asyncio
async def test_get_float_pv(engine: Engine, ioc: Server):
    query = """
query {
    getChannel(id: "pva://demo:float") {
        value {
            float
            string
        }
        display {
            widget
        }
    }
}
"""
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(float=2.0, string="2.000"), display=dict(widget="TEXTINPUT"),
            ),
        )
    )


@pytest.mark.asyncio
async def test_get_enum_pv(engine: Engine, ioc: Server):
    query = """
query {
    getChannel(id: "pva://demo:enum") {
        value {
            float
            string
        }
        display {
            widget
            choices
        }
    }
}
"""
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(float=1.0, string="ONE"),
                display=dict(widget="COMBO", choices=["ZERO", "ONE", "TWO"]),
            ),
        )
    )
