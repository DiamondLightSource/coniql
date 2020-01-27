# import curio
import asyncio
import aiohttp
from typing import AsyncGenerator, Optional, TypeVar, Dict

from coniql._types import ChannelQuality, NumberType, Range, NumberDisplay, \
    DisplayForm
from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel, \
    DEFAULT_TIMEOUT, WriteableChannel, ReadableChannel, MonitorableChannel
from device.devicetypes.result import Readback

T = TypeVar('T')

_SESSION = aiohttp.ClientSession()
_SERVER = 'http://localhost:8000/graphql'


class ProxyWriter(WriteableChannel):
    async def put(self, value: T, timeout: float = DEFAULT_TIMEOUT) -> \
            Readback[T]:
        aiohttp.request()


class ProxyReader(ReadableChannel):
    async def get(self, timeout: float = DEFAULT_TIMEOUT) -> Readback[T]:
        await _SESSION.get(_SERVER)


class ProxyMonitorer(MonitorableChannel):
    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        yield


class ReadWriteProxyChannel(ReadWriteChannel, ProxyWriter, ProxyReader,
                         ProxyMonitorer):
    pass


class ReadOnlyProxyChannel(ReadOnlyChannel, ProxyReader, ProxyMonitorer):
    pass
