# import curio
from typing import AsyncGenerator, TypeVar, Optional

from aioca._aioca import caget_one, FORMAT_TIME, connect, caput_one

from device.channel.ca.util import camonitor_as_async_generator, \
    value_to_readback_meta
from device.channel.channeltypes.channel import DEFAULT_TIMEOUT, \
    WriteableChannel, \
    ReadableChannel, MonitorableChannel
from device.channel.channeltypes.result import Readback

# Map from alarm.severity to ChannelQuality string

T = TypeVar('T')


class CaField:
    def __init__(self, pv: str, pv_prefix: Optional[str] = None,
                 rbv: Optional[str] = None, rbv_suffix: Optional[str] = None,
                 wait: bool = True, timeout: Optional[float] = None):
        pv_prefix = pv_prefix or ''
        self.pv = f'{pv_prefix}{pv}'
        self.rbv = rbv or f'{pv}{rbv_suffix}' if rbv_suffix is not None else None or pv
        self.wait = wait
        self.timeout = timeout or DEFAULT_TIMEOUT

    async def create_channel(self) -> 'CaChannel':
        await connect([self.pv, self.rbv])
        return CaChannel(self.pv, self.rbv, self.wait, self.timeout)


class CaChannel(ReadableChannel[T], WriteableChannel[T], MonitorableChannel[T]):
    def __init__(self, pv: str, rbv: str, wait: bool, timeout: float):
        self.pv = pv
        self.rbv = rbv
        self.wait = wait
        self.timeout = timeout

    async def put(self, value: T) -> Readback[T]:
        await caput_one(self.pv, value,
                              timeout=self.timeout,
                              wait=self.wait)
        return await self.get()

    async def get(self) -> Readback[T]:
        # try:
        value = await caget_one(self.rbv,
                                format=FORMAT_TIME,
                                timeout=self.timeout)
        return self.value_to_readback(value)
        # except Exception:  # TODO: Make more specific when aioca changes
        #     return Readback.not_connected()

    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        gen = camonitor_as_async_generator(self.rbv)
        async for value in gen:
            yield self.value_to_readback(value)

    def value_to_readback(self, value):
        time, status = value_to_readback_meta(value)
        return Readback(self.format_value(value), time, status)

    def format_value(self, value):
        return value.real
