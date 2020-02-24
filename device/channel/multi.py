import asyncio
from typing import Any, Iterable

from device.channel.channeltypes.channel import HasValue


async def get_all(*channels: HasValue[Any]) -> Iterable[Any]:
    return await asyncio.gather(*(map(lambda c: c.get(), channels)))
