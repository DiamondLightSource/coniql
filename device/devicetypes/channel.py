from typing import TypeVar, Generic, Iterable, AsyncGenerator, Coroutine, Any

from device.devicetypes.result import Result


T = TypeVar('T')


class ReadableChannel(Generic[T]):
    """A channel whose value can be read e.g. into a variable"""
    async def get(self) -> Result[T]:
        return NotImplemented


class MonitorableChannel(Generic[T]):
    """A channel whose value can be continuously monitored"""
    async def monitor(self) -> AsyncGenerator[Result[T], None]:
        yield NotImplemented


class WriteableChannel(Generic[T]):
    """A channel whose value can be mutated"""
    async def put(self, value: T) -> Result[T]:
        return NotImplemented


class ReadOnlyChannel(ReadableChannel[T], MonitorableChannel[T]):
    pass


class ReadWriteChannel(ReadOnlyChannel[T], WriteableChannel[T]):
    pass
