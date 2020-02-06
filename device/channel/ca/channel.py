# import curio
from typing import AsyncGenerator, TypeVar, Optional, Callable

from cothread import dbr, Timedout, aioca

from coniql._types import ChannelQuality, NumberType, Range, NumberDisplay, \
    DisplayForm, Time, ChannelStatus
from device.channel.ca.util import camonitor_as_async_generator
from device.channel.channeltypes.channel import DEFAULT_TIMEOUT, WriteableChannel, \
    ReadableChannel, MonitorableChannel, ConnectableChannel
from device.channel.channeltypes.connect import Connector
from device.channel.channeltypes.result import Readback

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


def connector(pv: str, rbv: Optional[str] = None,
              rbv_suffix: Optional[str] = None,
              wait: bool = True, timeout: Optional[float] = None) -> \
        Connector['CaChannel']:
    t_rbv = rbv or f'{pv}{rbv_suffix}' if rbv is not None else None or pv
    t_timeout = timeout or DEFAULT_TIMEOUT

    async def connect() -> CaChannel[T]:
        await aioca.connect([pv, rbv])
        channel: CaChannel = CaChannel(pv, t_rbv, wait, t_timeout)
        return channel

    return connect


def value_to_readback_meta(value):
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


class CaChannel(ReadableChannel[T], WriteableChannel[T], MonitorableChannel[T]):
    def __init__(self, pv: str, rbv: str, wait: bool = True,
                 timeout: float = DEFAULT_TIMEOUT):
        self.pv = pv
        self.rbv = rbv
        self.wait = wait
        self.timeout = timeout

    async def put(self, value: T) -> Readback[T]:
        await aioca.caput_one(self.pv, value,
                              timeout=self.timeout, wait=self.wait)
        return await self.get()

    async def get(self) -> Readback[T]:
        try:
            value = await aioca.caget_one(self.rbv, format=aioca.FORMAT_TIME,
                                          timeout=self.timeout)
            return self.value_to_readback(value)
        except Timedout:
            return Readback.not_connected()

    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        gen = camonitor_as_async_generator(self.rbv)
        async for value in gen:
            yield self.value_to_readback(value)

    def value_to_readback(self, value):
        time, status = value_to_readback_meta(value)
        return Readback(self.format_value(value), time, status)

    def format_value(self, value):
        return value.real
