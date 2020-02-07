from asyncio import Queue
from typing import TypeVar, AsyncGenerator

from device.channel.channeltypes.channel import WriteableChannel, ReadableChannel, MonitorableChannel
from device.channel.channeltypes.result import Readback

T = TypeVar('T')


class InMemoryReadOnlyChannel(ReadableChannel[T], MonitorableChannel[T]):
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


class InMemoryReadWriteChannel(InMemoryReadOnlyChannel[T], WriteableChannel[T]):
    async def put(self, value: T) -> Readback[T]:
        self.set_value(value)
        return await self.get()
