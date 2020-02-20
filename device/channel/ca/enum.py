from enum import EnumMeta, IntEnum
from typing_extensions import Protocol

from aioca._aioca import caget_one, FORMAT_CTRL

from device.channel.ca.channel import CaChannel


class CaEnum(CaChannel[str]):
    choices: EnumMeta

    async def setup(self):
        meta = await caget_one(self.pv, format=FORMAT_CTRL)
        self.choices = choices_from_meta(meta)

    async def get(self) -> str:
        value = await self.caget()
        choice = self.choices(value.real)
        return choice.name

    async def put(self, value: str) -> bool:
        inp = self.choices[value].real
        return await super(CaEnum, self).put(inp)


def choices_from_meta(meta) -> EnumMeta:
    choices: EnumMeta = IntEnum(meta.name, meta.enums, start=0)
    return choices
