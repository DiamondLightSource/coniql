import asyncio
from collections import Callable
from dataclasses import dataclass

from device.devicetypes.channel import ReadWriteChannel

_PREDICATE = Callable[[float], bool]
_SIDE_EFFECT = Callable[[], None]


@dataclass
class Trigger:
    input: ReadWriteChannel[float]
    predicate: ReadWriteChannel[_PREDICATE]
    output: ReadWriteChannel[bool]
    delay_seconds: ReadWriteChannel[float]

    async def run_in_memory(self):
        current = (await self.input.get()).value
        predicate = (await self.predicate.get()).value
        delay = (await self.delay_seconds.get()).value
        if predicate(current):
            await asyncio.sleep(delay)
            await self.output.put(True)


@dataclass
class FakeTriggerBox:
    trigger_1: Trigger
    trigger_2: Trigger

    min_seconds_between_checks: ReadWriteChannel[float]

    async def run_in_memory(self):
        while True:
            await asyncio.gather([
                self.trigger_1.run_in_memory,
                self.trigger_2.run_in_memory
            ])
            delay = await self.min_seconds_between_checks.get()
            await asyncio.sleep(delay.value)
