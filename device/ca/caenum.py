import asyncio
from enum import IntEnum
from typing import Optional

from device.ca.channel import CaChannel
from device.devicetypes.channel import DEFAULT_TIMEOUT
from device.devicetypes.result import Readback


class CaEnum(CaChannel[str]):
    def __init__(self, pv: str, rbv: Optional[str] = None,
                 rbv_suffix: Optional[str] = None,
                 timeout: float = DEFAULT_TIMEOUT):
        super().__init__(pv, rbv, rbv_suffix, timeout)
        self.choices = None

    async def connect(self):
        meta = await self.raw.get_meta()
        e = IntEnum(meta.name, meta.enums, start=0)
        self.choices = e

    async def put(self, value: str) -> Readback[str]:
        inp = self.choices[value].real
        return await super().put(inp)

    def format_value(self, value):
        choice = self.choices(value.real)
        return choice.name
