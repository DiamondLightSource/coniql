from typing import TypeVar, Generic, AsyncGenerator, Union
from typing_extensions import Protocol

from device.channel.channeltypes.result import Readback


TChannel = TypeVar('TChannel')
TValue = TypeVar('TValue')
DEFAULT_TIMEOUT = 10.0  # seconds


class ChannelFactory(Generic[TChannel]):
    async def create_channel(self) -> TChannel:
        raise NotImplementedError


class ReadableChannel(Protocol[TValue]):
    """A channel whose value can be read e.g. into a variable"""
    async def get(self) -> Readback[TValue]:
        return NotImplemented


class MonitorableChannel(Protocol[TValue]):
    """A channel whose value can be continuously monitored"""
    async def monitor(self) -> AsyncGenerator[Readback[TValue], None]:
        yield NotImplemented


class WriteableChannel(Protocol[TValue]):
    """A channel whose value can be mutated"""
    async def put(self, value: TValue) -> Readback[TValue]:
        return NotImplemented


class ReadWriteChannel(Protocol[TValue], ReadableChannel[TValue],
                       WriteableChannel[TValue], MonitorableChannel[TValue]):
    pass


class ReadOnlyChannel(Protocol[TValue], ReadableChannel[TValue],
                      MonitorableChannel[TValue]):
    pass
