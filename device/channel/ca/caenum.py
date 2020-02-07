from enum import IntEnum, EnumMeta
from typing import Optional

import aioca

from device.channel.ca.channel import CaChannel, CaField
from device.channel.channeltypes.channel import DEFAULT_TIMEOUT
from device.channel.channeltypes.result import Readback


class CaEnum(CaField):
    async def create_channel(self) -> 'CaEnumChannel':
        meta = await aioca.caget(self.pv, format=aioca.FORMAT_CTRL)
        choices = choices_from_meta(meta)
        return CaEnumChannel(self.pv, self.rbv, choices, self.wait,
                             self.timeout)


class CaEnumChannel(CaChannel[str]):
    def __init__(self, pv: str, rbv: str, choices: EnumMeta,
                 wait: bool = True, timeout: float = DEFAULT_TIMEOUT):
        super().__init__(pv, rbv, wait, timeout)
        self.choices = choices

    async def put(self, value: str) -> Readback[str]:
        inp = self.choices[value].real
        return await super().put(inp)

    def format_value(self, value):
        choice = self.choices(value.real)
        return choice.name


def choices_from_meta(meta) -> EnumMeta:
    choices: EnumMeta = IntEnum(meta.name, meta.enums, start=0)
    return choices
