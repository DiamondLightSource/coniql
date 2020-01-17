import asyncio

from asyncio import Queue
from collections import Iterable
from typing import TypeVar, AsyncGenerator, Coroutine, Any, Generic, Type, \
    Callable, List, Optional

from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel
from device.devicetypes.result import Result
from device.mock.result import MockWorkingResult

T = TypeVar('T')
_SUBSCRIBER = Callable[[T], None]


class MockReadOnlyChannel(ReadOnlyChannel[T]):
    def __init__(self, value: T):
        self.__value = value

    def set_value(self, value: T):
        self.__value = value

    async def get(self) -> Result[T]:
        return MockWorkingResult(self.__value)

    async def monitor(self) -> AsyncGenerator[Result[T], None]:
        queue: Queue = Queue()
        await queue.put(self.get())
        while True:
            yield await queue.get()


class MockReadWriteChannel(MockReadOnlyChannel[T], ReadWriteChannel[T]):
    async def put(self, value: T) -> Result[T]:
        self.set_value(value)
        return MockWorkingResult(value)
