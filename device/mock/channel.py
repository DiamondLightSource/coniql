import asyncio

from asyncio import Queue
from collections import Iterable
from typing import TypeVar, AsyncGenerator, Coroutine, Any, Generic

from device.types.channel import ReadOnlyChannel, ReadWriteChannel
from device.types.result import Result
from device.mock.result import MockWorkingResult

T = TypeVar('T')


class MockReadOnlyChannel(ReadOnlyChannel[T]):
    def __init__(self, value: T):
        self.__value = value

    def get(self) -> Result[T]:
        return MockWorkingResult(self.__value)

    async def get_async(self) -> Result[T]:
        return self.get()

    async def monitor(self) -> AsyncGenerator[Result[T], None]:
        queue: Queue = Queue()

        await queue.put(self.get())

        while True:
            yield await queue.get()


class MockReadWriteChannel(MockReadOnlyChannel[T]):
    def put(self, value: T) -> Result[T]:
        self.__value = value
        return MockWorkingResult(self.__value)

    def put_async(self, value: T) -> Result[T]:
        return self.put(value)