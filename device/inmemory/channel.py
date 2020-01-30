import asyncio

from asyncio import Queue
from collections import Iterable
from typing import TypeVar, AsyncGenerator, Coroutine, Any, Generic, Type, \
    Callable, List, Optional

from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel, \
    DEFAULT_TIMEOUT
from device.devicetypes.result import Readback

T = TypeVar('T')


class InMemoryReadOnlyChannel(ReadOnlyChannel[T]):
    def __init__(self, value: T):
        self.__value = value

    def set_value(self, value: T):
        self.__value = value

    async def get(self) -> Readback[T]:
        return Readback.ok(self.__value, mutable=False)

    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        queue: Queue = Queue()
        await queue.put(self.get())
        while True:
            yield await queue.get()


class InMemoryReadWriteChannel(InMemoryReadOnlyChannel[T], ReadWriteChannel[T]):
    async def put(self, value: T) -> Readback[T]:
        self.set_value(value)
        return await self.get()
