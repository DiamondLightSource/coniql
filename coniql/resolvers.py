import asyncio

from annotypes import Anno, add_call_types
from p4p.client.asyncio import Context, Value

with Anno("Who to greet"):
    APerson = str
with Anno("The greeting to return"):
    AGreeting = str


@add_call_types
def say_hello(person: APerson="me") -> AGreeting:
    """Say hello to person"""
    return f'Hello %s' % person


async def subscribe_float(root, info, channel: str):
    with Context("pva", unwrap={}) as ctxt:
        print(channel)
        q = asyncio.Queue()
        ctxt.monitor(channel, q.put)
        while True:
            value = await q.get()  # type: Value
            data = dict(
                typeid=value.getID(),
                value=value.value
            )
            yield dict(subscribeFloatScalar=data)
