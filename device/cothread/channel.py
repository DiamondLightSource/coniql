# import curio
import asyncio
from typing import AsyncGenerator, Optional, TypeVar, Dict

from cothread import dbr
from cothread.aioca import caput_one, caget_one, camonitor, FORMAT_TIME

from coniql._types import ChannelQuality, NumberType, Range, NumberDisplay, \
    DisplayForm
from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel, \
    DEFAULT_TIMEOUT, WriteableChannel, ReadableChannel, MonitorableChannel
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
EMPTY_DISPLAY = NumberDisplay(EMPTY_RANGE, EMPTY_RANGE, EMPTY_RANGE,
                              EMPTY_RANGE, "", 4, DisplayForm.DEFAULT)

T = TypeVar('T')


class PvRef:
    def __init__(self, pv: str, rbv: Optional[str] = None,
                 rbv_suffix: Optional[str] = None):
        self.pv = pv
        self.rbv = rbv or f'{pv}{rbv_suffix}' if rbv is not None else None or pv


class CaWriter(PvRef, WriteableChannel):
    async def put(self, value: T, timeout: float = DEFAULT_TIMEOUT) -> \
            Readback[T]:
        await caput_one(self.pv, value, timeout=timeout)
        readback = await caget_one(self.rbv, timeout=timeout)
        return readback


class CaReader(PvRef, ReadableChannel):
    async def get(self, timeout: float = DEFAULT_TIMEOUT) -> Readback[T]:
        value = await caget_one(self.rbv, format=FORMAT_TIME, timeout=timeout)
        return Readback.ok(value, mutable=True)


class CaMonitorer(PvRef, MonitorableChannel):
    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        q = asyncio.Queue()

        def queue_callback(value):
            asyncio.create_task(q.put(value))

        m = await camonitor(self.rbv, queue_callback, format=FORMAT_TIME)
        while True:
            yield Readback.ok(await q.get(), mutable=False)


class ReadWriteCaChannel(ReadWriteChannel, CaWriter, CaReader,
                         CaMonitorer):
    pass


class ReadOnlyCaChannel(ReadOnlyChannel, CaReader, CaMonitorer):
    pass
