import asyncio

from typing import TypeVar, AsyncGenerator

from device.channel.channeltypes.channel import ConnectableChannel, WriteableChannel, \
    ReadableChannel, MonitorableChannel
from device.channel.channeltypes.result import Readback
from device.channel.pandablocks.pandablocksclient import PandABlocksClient


T = TypeVar('T')


class PandAFieldChannel(ReadableChannel[T], WriteableChannel[T],
                        MonitorableChannel[T], ConnectableChannel):
    def __init__(self, client: PandABlocksClient,
                 block_name: str, field_name: str):
        self.client = client
        self.block_name = block_name
        self.field_name = field_name

    async def connect(self):
        pass  # TODO: Connecting should happen elsewhere, same for CA channels

    async def put(self, value: T) -> Readback[T]:
        try:
            self.client.set_field(self.block_name, self.field_name, value)
            return await self.get()  # TODO: Not quite right!
        except ValueError:
            return Readback.not_connected()

    async def monitor(self) -> AsyncGenerator[Readback[T], None]:
        """TODO: Very rudimentary polling-based implementation,
            can we do better?"""
        while True:
            await asyncio.sleep(1.0)
            yield await self.get()

    async def get(self) -> Readback[T]:
        try:
            value = self.client.get_field(self.block_name, self.field_name)
            return Readback.ok(value, mutable=True)
        except ValueError:
            return Readback.not_connected()  # TODO: Not quite right!
