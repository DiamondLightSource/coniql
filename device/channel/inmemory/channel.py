from asyncio import Queue
from typing import TypeVar, AsyncGenerator, Generic


T = TypeVar('T')


class InMemoryReadOnlyChannel(Generic[T]):
    def __init__(self, value: T):
        self.__value = value

    def set_value(self, value: T):
        self.__value = value

    async def get(self) -> T:
        return self.__value

    async def monitor(self) -> AsyncGenerator[T, None]:
        queue: Queue = Queue()
        await queue.put(self.get())
        while True:
            yield await queue.get()


class InMemoryReadWriteChannel(InMemoryReadOnlyChannel[T]):
    async def put(self, value: T) -> bool:
        self.set_value(value)
        return True
