import asyncio

from typing import Dict, Any, List, TypeVar, Optional
from datetime import datetime, timedelta

from device.devicetypes.channel import ReadWriteChannel, ReadOnlyChannel, \
    MonitorableChannel
from device.devicetypes.result import Readback

_PUT_DICT = Dict[ReadWriteChannel, Any]
_READBACK_DICT = Dict[ReadOnlyChannel, Readback[Any]]


async def put_all(channel_values: _PUT_DICT) -> _READBACK_DICT:
    results = await asyncio.gather(*(channel.put(value)
                                     for channel, value in
                                     channel_values.items()))
    return {channel: result
            for channel, result in zip(channel_values.keys(), results)}


async def get_all(channels: List[ReadOnlyChannel]) -> _READBACK_DICT:
    results = await asyncio.gather(*(channel.get() for channel in channels))
    return {channel: result
            for channel, result in zip(channels, results)}


T = TypeVar('T')


# TODO: Generic predicate handling!
async def await_value(channel: MonitorableChannel[T], value: T,
                      timeout: Optional[float] = None) -> Optional[Readback[T]]:
    latest_time = datetime.now() + timedelta(seconds=timeout or 0)
    async for readback in channel.monitor():
        if readback.value == value:
            return readback
        if timeout is not None and datetime.now() > latest_time:
            break
    return None
