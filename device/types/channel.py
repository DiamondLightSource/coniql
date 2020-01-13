from typing import TypeVar, Generic, Iterable, AsyncGenerator, Coroutine, Any

from device.types.result import Result

T = TypeVar('T')


class ReadOnlyChannel(Generic[T]):
    def get(self) -> Result[T]:
        return NotImplemented

    async def get_async(self) -> Result[T]:
        return NotImplemented

    async def monitor(self) -> AsyncGenerator[Result[T], None]:
        yield NotImplemented


class ReadWriteChannel(ReadOnlyChannel[T]):
    def put(self, value: T) -> Result[T]:
        return NotImplemented

    def put_async(self, value: T) -> Result[T]:
        return NotImplemented
