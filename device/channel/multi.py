import asyncio
from typing import Any, Iterable, Dict

from device.channel.channeltypes.channel import HasValue


async def get_all(*channels: HasValue[Any]) -> Iterable[Any]:
    """Concurrently reads the values of all channels supplied"""
    return await asyncio.gather(*map(lambda c: c.get(), channels))
