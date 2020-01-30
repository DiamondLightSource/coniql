# import curio
import asyncio
from dataclasses import dataclass
from enum import IntEnum
from typing import AsyncGenerator, Optional, TypeVar, Dict, Generic, Callable, \
    Any

from cothread import dbr, Timedout
from cothread.aioca import caput_one, caget_one, camonitor, FORMAT_TIME, \
    FORMAT_CTRL

from coniql._types import ChannelQuality, NumberType, Range, NumberDisplay, \
    DisplayForm, Time, ChannelStatus
from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel, \
    DEFAULT_TIMEOUT, WriteableChannel, ReadableChannel, MonitorableChannel
from device.devicetypes.result import Readback

from aiostream import pipe

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
U = TypeVar('U')


@dataclass
class CaDef:
    pv: str
    rbv: str

    @classmethod
    def for_single_pv(cls, pv: str):
        return CaDef(pv, pv)

    @classmethod
    def with_rbv_prefix(cls, pv: str, rbv_prefix: str):
        return CaDef(pv, f'{pv}{rbv_prefix}')


class RawCaChannel(Generic[T]):
    def __init__(self, cadef: CaDef):
        self.cadef = cadef

    async def get_meta(self, timeout: float = DEFAULT_TIMEOUT):
        return await caget_one(self.cadef.rbv, format=FORMAT_CTRL,
                               timeout=timeout)

    async def get(self, timeout: float = DEFAULT_TIMEOUT) -> T:
        value = await caget_one(self.cadef.rbv,
                                format=FORMAT_TIME, timeout=timeout)
        return value

    async def put(self, value: T, timeout: float = DEFAULT_TIMEOUT):
        return await caput_one(self.cadef.pv, value, timeout=timeout)

    async def monitor(self) -> AsyncGenerator[T, None]:
        q: asyncio.Queue = asyncio.Queue()

        def queue_callback(value):
            asyncio.create_task(q.put(value))

        subscription = await camonitor(self.cadef.rbv,
                                       queue_callback, format=FORMAT_TIME)
        try:
            while True:
                yield await q.get()
        finally:
            subscription.close()


class CaChannel(ReadableChannel[T], WriteableChannel[T], MonitorableChannel[T]):
    # def __init__(self, pv: str, rbv: Optional[str] = None,
    #              rbv_suffix: Optional[str] = None):
    #     self.pv = pv
    #     self.rbv = rbv or f'{pv}{rbv_suffix}' if rbv is not None else None or pv

    def __init__(self, raw: RawCaChannel[T]):
        self.raw = raw

    async def put(self, value: T, timeout: float = DEFAULT_TIMEOUT) -> \
            Readback[T]:
        await self.raw.put(value, timeout)
        return await self.get(timeout=timeout)

    async def get(self, timeout: float = DEFAULT_TIMEOUT) -> Readback[T]:
        try:
            value = await self.raw.get(timeout)
            return self.value_to_readback(value)
        except Timedout:
            return Readback.not_connected()

    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        gen = self.raw.monitor()
        async for value in gen:
            yield self.value_to_readback(value)

    def value_to_readback(self, value):
        time, status = self.value_to_readback_meta(value)
        return Readback(self.format_value(value), time, status)

    def format_value(self, value):
        return value.real

    def value_to_readback_meta(self, value):
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


class CaBool(CaChannel[bool]):
    async def put(self, value: T, timeout: float = DEFAULT_TIMEOUT) -> \
            Readback[T]:
        return await super().put(int(value), timeout)

    def format_value(self, value):
        return bool(value.real)


class CaEnum(CaChannel[str]):
    async def __choices(self) -> IntEnum:
        meta_value = await self.raw.get_meta()
        choices = meta_value.enums
        return IntEnum(meta_value.name, choices)

    async def put(self, value: str, timeout: float = DEFAULT_TIMEOUT) -> \
            Readback[str]:
        choices = await self.__choices()
        inp = choices[value].real
        return await super().put(inp, timeout)

    def format_value(self, value):
        choices = await self.__choices()
        return choices(value.real)
