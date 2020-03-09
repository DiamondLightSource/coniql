import asyncio
from typing import AsyncGenerator, Any

from aioca import FORMAT_TIME, camonitor


async def camonitor_as_async_generator(pv: str, format=FORMAT_TIME) -> \
        AsyncGenerator[Any, None]:
    """runs aioca.camonitor and provides the callback results in the form
    of an asynchronous generator, which is similar to a stream"""
    q: asyncio.Queue = asyncio.Queue()

    def queue_callback(value):
        asyncio.create_task(q.put(value))

    subscription = await camonitor(pv, queue_callback, format=format)
    try:
        while True:
            yield await q.get()
    finally:
        # TODO: Figure out why subscription is sometimes None
        if subscription is not None:
            subscription.close()
