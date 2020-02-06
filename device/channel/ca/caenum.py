from enum import IntEnum, EnumMeta
from typing import Optional

from cothread import aioca

from device.channel.ca.channel import CaChannel
from device.channel.channeltypes.channel import DEFAULT_TIMEOUT
from device.channel.channeltypes.result import Readback


class CaEnum(CaChannel[str]):
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


async def connect(pv: str, rbv: Optional[str] = None,
                    rbv_suffix: Optional[str] = None,
                    wait: bool = True, timeout: Optional[float] = None) -> \
        CaEnum:
    t_rbv = rbv or f'{pv}{rbv_suffix}' if rbv is not None else None or pv
    t_timeout = timeout or DEFAULT_TIMEOUT

    await aioca.connect([pv, t_rbv])
    meta = await aioca.caget(pv, format=aioca.FORMAT_CTRL)
    choices = choices_from_meta(meta)
    channel = CaEnum(pv, t_rbv, choices, wait, t_timeout)
    return channel


def choices_from_meta(meta) -> EnumMeta:
    choices: EnumMeta = IntEnum(meta.name, meta.enums, start=0)
    return choices
