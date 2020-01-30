from enum import IntEnum

from device.cothread.channel import CaChannel
from device.devicetypes.channel import DEFAULT_TIMEOUT
from device.devicetypes.result import Readback


class CaEnum(CaChannel[str]):
    async def __choices(self) -> IntEnum:
        meta_value = await self.raw.get_meta()
        choices = meta_value.enums
        return IntEnum(meta_value.name, choices)

    async def put(self, value: str) -> Readback[str]:
        choices = await self.__choices()
        inp = choices[value].real
        return await super().put(inp)

    def format_value(self, value):
        choices = await self.__choices()
        return choices(value.real)
