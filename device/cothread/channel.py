# import curio
import asyncio
from typing import AsyncGenerator, Optional, TypeVar, Dict

from cothread import dbr
from cothread.aioca import caput_one, caget_one, camonitor, FORMAT_TIME

from coniql._types import ChannelQuality, NumberType, Range, NumberDisplay, \
    DisplayForm
from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel, \
    DEFAULT_TIMEOUT
from device.devicetypes.result import Readback


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

# Map from alarm.severity to ChannelQuality string
CHANNEL_QUALITY_MAP = [
    ChannelQuality.VALID,
    ChannelQuality.WARNING,
    ChannelQuality.ALARM,
    ChannelQuality.INVALID,
    ChannelQuality.UNDEFINED,
]

EMPTY_RANGE = Range(0, 0)
EMPTY_DISPLAY = NumberDisplay(EMPTY_RANGE, EMPTY_RANGE, EMPTY_RANGE, EMPTY_RANGE, "", 4, DisplayForm.DEFAULT)


T = TypeVar('T')


class ReadOnlyCaChannel(ReadOnlyChannel):
    def __init__(self, pv: str):
        self.pv = pv

    async def get(self, timeout: float = DEFAULT_TIMEOUT) -> Readback[T]:
        value = await caget_one(self.pv, format=FORMAT_TIME, timeout=timeout)
        return Readback.ok(value, mutable=False)

    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        q = asyncio.Queue()

        def queue_callback(value):
            asyncio.create_task(q.put(value))

        m = await camonitor(self.pv, queue_callback, format=FORMAT_TIME)
        while True:
            yield Readback.ok(await q.get(), mutable=False)


class ReadWriteCaChannel(ReadWriteChannel):
    def __init__(self, pv: str):
        self.pv = pv

    async def get(self, timeout: float = DEFAULT_TIMEOUT) -> Readback[T]:
        value = await caget_one(self.pv, format=FORMAT_TIME, timeout=timeout)
        return Readback.ok(value, mutable=True)

    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        q = asyncio.Queue()

        def queue_callback(value):
            asyncio.create_task(q.put(value))

        m = await camonitor(self.pv, queue_callback, format=FORMAT_TIME)
        while True:
            yield Readback.ok(await q.get(), mutable=True)
        m.close()

    async def put(self, value: T, timeout: float = DEFAULT_TIMEOUT) -> Readback[T]:
        await caput_one(self.pv, value, timeout=timeout)
        readback = await self.get(timeout)
        return readback
