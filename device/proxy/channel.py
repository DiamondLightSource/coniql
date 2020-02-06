# import curio
import aiohttp
from typing import AsyncGenerator, TypeVar

from device.channel.channeltypes.channel import ReadOnlyChannel, ReadWriteChannel, \
    DEFAULT_TIMEOUT, WriteableChannel, ReadableChannel, MonitorableChannel
from device.channel.channeltypes.result import Readback

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
