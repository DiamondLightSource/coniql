from enum import EnumMeta, IntEnum
from typing_extensions import Protocol

from aioca._aioca import caget_one, FORMAT_CTRL

from device.channel.ca.channel import CaChannel


class CaEnum(CaChannel[str]):
    choices: EnumMeta

    def __await__(self):
        meta = caget_one(self.pv, format=FORMAT_CTRL).__await__()
        self.choices = choices_from_meta(meta)
        return meta

    async def get(self) -> str:
        value = await self.caget()
        choice = self.choices(value.real)
        return choice.name

    async def put(self, value: str) -> bool:
        inp = self.choices[value].real
        return super(CaEnum, self).put(inp)


def choices_from_meta(meta) -> EnumMeta:
    choices: EnumMeta = IntEnum(meta.name, meta.enums, start=0)
    return choices
