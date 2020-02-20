import asyncio

from typing import Dict, Any, List, TypeVar, Optional, Coroutine, Iterable
from datetime import datetime, timedelta

from device.channel.channeltypes.channel import CanMonitorValue, CanPutValue, \
    HasValue


# async def put_all(channel_values: _PUT_DICT) -> _READBACK_DICT:
#     results = await asyncio.gather(*(channel.put(value)
#                                      for channel, value in
#                                      channel_values.items()))
#     return {channel: result
#             for channel, result in zip(channel_values.keys(), results)}
#
#
# async def get_all(channels: List[HasValue]) -> _READBACK_DICT:
#     return await asyncio.gather(*(channel.get() for channel in channels))


T = TypeVar('T')


# TODO: Generic predicate handling!
async def await_value(channel: CanMonitorValue[T], value: T,
                      timeout: Optional[float] = None) -> Optional[Readback[T]]:
    latest_time = datetime.now() + timedelta(seconds=timeout or 0)
    async for readback in channel.monitor():
        if readback.value == value:
            return readback
        if timeout is not None and datetime.now() > latest_time:
            break
    return None


async def asyncio_gather_values(coros: Dict[Any, Coroutine[Any, Any, Any]]) -> \
        Dict[Any, Any]:
    ts = [wrap_coro(key, coro)() for key, coro in coros.items()]
    rs = await asyncio.gather(*ts)
    return {
        k: v for k, v in rs
    }


def wrap_coro(meta, coro):
    async def wrapper():
        coro_result = await coro
        return meta, coro_result

    return wrapper
