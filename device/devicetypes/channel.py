from typing import TypeVar, Generic, Iterable, AsyncGenerator, Coroutine, Any, \
    Union

from device.devicetypes.result import Readback


T = TypeVar('T')
DEFAULT_TIMEOUT = 10.0  # seconds


class ConnectableChannel:
    async def connect(self):
        raise NotImplementedError


class ReadableChannel(Generic[T]):
    """A channel whose value can be read e.g. into a variable"""
    async def get(self) -> Readback[T]:
        return NotImplemented


class MonitorableChannel(Generic[T]):
    """A channel whose value can be continuously monitored"""
    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        yield NotImplemented


class WriteableChannel(Generic[T]):
    """A channel whose value can be mutated"""
    async def put(self, value: T) -> Readback[T]:
        return NotImplemented


ReadOnlyChannel = Union[ReadableChannel[T], MonitorableChannel[T]]

ReadWriteChannel = Union[ReadableChannel[T], MonitorableChannel[T],
                         WriteableChannel[T]]
