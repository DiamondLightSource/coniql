import asyncio

from typing import TypeVar, AsyncGenerator, Generic, List, Optional, Callable, \
    Awaitable

T = TypeVar('T')


class InMemoryReadOnlyChannel(Generic[T]):
    """Immutable channel that holds a value in memeory, useful for storing
    config in memory"""

    def __init__(self, value: T):
        self._value = value

    async def get(self) -> T:
        return self._value


_Callback = Callable[[T], Awaitable]


class InMemoryReadWriteChannel(InMemoryReadOnlyChannel[T]):
    """Mutable and monitorable channel that holds a value in memory. Useful for
    testing"""
    def __init__(self, value: T,
                 callbacks: Optional[List[_Callback]] = None):
        super().__init__(value)
        self.callbacks = callbacks or []

    async def put(self, value: T) -> bool:
        self._value = value
        await self.__notify_all()
        return True

    async def __notify_all(self):
        for callback in self.callbacks:
            await callback(self._value)

    async def monitor(self) -> AsyncGenerator[T, None]:
        # Yield initial value at the time of subscription
        yield self._value

        # Yield subsequent values on change
        try:
            queue: asyncio.Queue = asyncio.Queue()
            self.callbacks.append(queue.put)
            while True:
                yield await queue.get()
        finally:
            self.callbacks.remove(queue.put)
