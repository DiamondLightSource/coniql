# import curio
from typing import AsyncGenerator, TypeVar, Optional

from cothread import Timedout, aioca

from device.channel.ca.util import camonitor_as_async_generator, \
    value_to_readback_meta
from device.channel.channeltypes.channel import DEFAULT_TIMEOUT, \
    WriteableChannel, \
    ReadableChannel, MonitorableChannel
from device.channel.channeltypes.result import Readback

# Map from alarm.severity to ChannelQuality string

T = TypeVar('T')


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


async def connect(pv: str, rbv: Optional[str] = None,
                  rbv_suffix: Optional[str] = None,
                  wait: bool = True, timeout: Optional[float] = None) -> \
        CaChannel:
    t_rbv = rbv or f'{pv}{rbv_suffix}' if rbv is not None else None or pv
    t_timeout = timeout or DEFAULT_TIMEOUT
    await aioca.connect([pv, t_rbv])
    channel: CaChannel = CaChannel(pv, t_rbv, wait, t_timeout)
    return channel
