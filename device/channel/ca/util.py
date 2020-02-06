import asyncio
from typing import AsyncGenerator, Any, Tuple

from cothread import dbr
from cothread.aioca import FORMAT_TIME, camonitor

from coniql._types import NumberType, ChannelQuality, Range, NumberDisplay, \
    DisplayForm, Time, ChannelStatus


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
        subscription.close()


NUMBER_TYPES = {
    dbr.DBR_CHAR: NumberType.INT8,
    dbr.DBR_SHORT: NumberType.INT16,
    dbr.DBR_LONG: NumberType.INT64,
    dbr.DBR_FLOAT: NumberType.FLOAT32,
    dbr.DBR_DOUBLE: NumberType.FLOAT64
}
OTHER_TYPES = {
    dbr.DBR_ENUM: "Enum",
    dbr.DBR_STRING: "String"
}
CHANNEL_QUALITY_MAP = [
    ChannelQuality.VALID,
    ChannelQuality.WARNING,
    ChannelQuality.ALARM,
    ChannelQuality.INVALID,
    ChannelQuality.UNDEFINED,
]
EMPTY_RANGE = Range(0, 0)
EMPTY_DISPLAY = NumberDisplay(EMPTY_RANGE, EMPTY_RANGE, EMPTY_RANGE,
                              EMPTY_RANGE, "", 4, DisplayForm.DEFAULT)


def value_to_readback_meta(value) -> Tuple[Time, ChannelStatus]:
    timestamp = value.timestamp
    time = Time(
        seconds=int(timestamp),
        nanoseconds=int((timestamp % 1) * 1e9),
        userTag=0
    )
    status = ChannelStatus(
        quality=CHANNEL_QUALITY_MAP[value.severity],
        message="alarm",
        mutable=True
    )
    return time, status
