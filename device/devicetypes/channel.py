from typing import TypeVar, Generic, Iterable, AsyncGenerator, Coroutine, Any

from device.devicetypes.result import Readback


T = TypeVar('T')
DEFAULT_TIMEOUT = 10.0  # seconds


class ReadableChannel(Generic[T]):
    """A channel whose value can be read e.g. into a variable"""
    async def get(self, timeout: float = DEFAULT_TIMEOUT) -> Readback[T]:
        return NotImplemented


class MonitorableChannel(Generic[T]):
    """A channel whose value can be continuously monitored"""
    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        yield NotImplemented


class WriteableChannel(Generic[T]):
    """A channel whose value can be mutated"""
    async def put(self, value: T, timeout: float = DEFAULT_TIMEOUT) -> Readback[T]:
        return NotImplemented


class ReadOnlyChannel(ReadableChannel[T], MonitorableChannel[T]):
    pass


class ReadWriteChannel(ReadOnlyChannel[T], WriteableChannel[T]):
    pass
