from typing import TypeVar, Generic, AsyncGenerator, Union

from device.channel.channeltypes.result import Readback


TChannel = TypeVar('TChannel')
TValue = TypeVar('TValue')
DEFAULT_TIMEOUT = 10.0  # seconds


class ChannelFactory(Generic[TChannel]):
    async def create_channel(self) -> TChannel:
        raise NotImplementedError


class ReadableChannel(Generic[TValue]):
    """A channel whose value can be read e.g. into a variable"""
    async def get(self) -> Readback[TValue]:
        return NotImplemented


class MonitorableChannel(Generic[TValue]):
    """A channel whose value can be continuously monitored"""
    async def monitor(self) -> AsyncGenerator[Readback[TValue], None]:
        yield NotImplemented


class WriteableChannel(Generic[TValue]):
    """A channel whose value can be mutated"""
    async def put(self, value: TValue) -> Readback[TValue]:
        return NotImplemented


ReadOnlyChannel = Union[ReadableChannel[TValue], MonitorableChannel[TValue]]

ReadWriteChannel = Union[ReadableChannel[TValue], MonitorableChannel[TValue],
                         WriteableChannel[TValue]]
