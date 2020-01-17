from typing import TypeVar, Generic, Iterable, AsyncGenerator, Coroutine, Any

from device.devicetypes.result import Result


T = TypeVar('T')


class ReadableChannel(Generic[T]):
    async def get(self) -> Result[T]:
        return NotImplemented


class MonitorableChannel(Generic[T]):
    async def monitor(self) -> AsyncGenerator[Result[T], None]:
        yield NotImplemented


class WriteableChannel(Generic[T]):
    async def put(self, value: T) -> Result[T]:
        return NotImplemented


class ReadOnlyChannel(ReadableChannel[T], MonitorableChannel[T]):
    pass


class ReadWriteChannel(ReadOnlyChannel[T], WriteableChannel[T]):
    pass


# class ReadOnlyChannel(Generic[T]):
#     def get(self) -> Result[T]:
#         return NotImplemented
#
#     async def get_async(self) -> Result[T]:
#         return NotImplemented
#
#     async def monitor(self) -> AsyncGenerator[Result[T], None]:
#         yield NotImplemented
#
#
# class ReadWriteChannel(ReadOnlyChannel[T]):
#     def put(self, value: T) -> Result[T]:
#         return NotImplemented
#
#     async def put_async(self, value: T) -> Result[T]:
#         return NotImplemented
