import asyncio
from typing import AsyncGenerator, Any, Tuple

from aioca import FORMAT_TIME, camonitor, _dbr as dbr

from coniql._types import NumberType, ChannelQuality, Range, NumberDisplay, \
    DisplayForm, Time, ChannelStatus, Readback


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


def ca_value_to_readback(value: Any, ca_value) -> Readback:
    return Readback(
        value=value,
        time=time_from_ca_timestamp(ca_value.timestamp),
        status=status_from_ca_value(ca_value)
    )


def time_from_ca_timestamp(timestamp: float) -> Time:
    return Time(
        seconds=int(timestamp),
        nanoseconds=int((timestamp % 1) * 1e9),
        userTag=0
    )


def status_from_ca_value(ca_value) -> ChannelStatus:
    return ChannelStatus(
        quality=CHANNEL_QUALITY_MAP[ca_value.severity],
        message="alarm",
        mutable=True
    )
