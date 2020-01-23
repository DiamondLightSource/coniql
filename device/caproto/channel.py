# import curio
import asyncio
from typing import AsyncGenerator, Optional, TypeVar, Dict
from cothread import catools

from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel
from device.devicetypes.result import Result
from device.inmemory.result import MockWorkingResult

T = TypeVar('T')


class CaChannel(ReadWriteChannel):
    def __init__(self, pv: str):
        self.pv = pv

    async def get(self) -> Result[T]:
        # TODO: Datatypes
        raw_result = catools.caget_one(self.pv)
        return MockWorkingResult(raw_result.real)

    async def monitor(self) -> AsyncGenerator[Result[T], None]:
        queue = asyncio.Queue()

        async def put(item):
            await queue.put(item)

        catools.camonitor(self.pv, put)
        while True:
            yield await queue.get()

    async def put(self, value: T) -> Result[T]:
        print(f'{self.pv}.put({value})')
        catools.caput_one(self.pv, value, wait=True)
        print('Done')
        return MockWorkingResult(value) # TODO: Sort out results
