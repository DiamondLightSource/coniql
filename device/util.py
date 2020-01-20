import asyncio

from typing import Dict, Any, List

from device.devicetypes.channel import ReadWriteChannel, ReadOnlyChannel
from device.devicetypes.result import Result

_PUT_DICT = Dict[ReadWriteChannel, Any]
_READBACK_DICT = Dict[ReadOnlyChannel, Result[Any]]


async def put_all(channel_values: _PUT_DICT) -> _READBACK_DICT:
    results = await asyncio.gather(*(channel.put(value)
                                     for channel, value in channel_values.items()))
    return {channel: result
            for channel, result in zip(channel_values.keys(), results)}


async def get_all(channels: List[ReadOnlyChannel]) -> _READBACK_DICT:
    results = await asyncio.gather(*(channel.get() for channel in channels))
    return {channel: result
            for channel, result in zip(channels, results)}
