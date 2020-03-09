from enum import EnumMeta, IntEnum
from typing_extensions import Protocol

from aioca._aioca import caget_one, FORMAT_CTRL

from device.channel.ca.channel import CaChannel


class CaEnum(CaChannel[str]):
    """A channel representing an Enum over channel access."""
    choices: EnumMeta

    async def setup(self):
        """Retrieves the Enum choices from the channel, sets them as part of
        object state"""
        meta = await caget_one(self.pv, format=FORMAT_CTRL)
        self.choices = choices_from_meta(meta)

    def format_value(self, value) -> str:
        choice = self.choices(value.real)
        return choice.name

    async def put(self, value: str) -> bool:
        inp = self.choices[value].real
        return await super(CaEnum, self).put(inp)


def choices_from_meta(meta) -> EnumMeta:
    """Creates a dynamic, serializable enum. Values can be checked agains this
    enum."""
    # TODO: MyPy doesn't like this for some reason
    choices: EnumMeta = IntEnum(meta.name, meta.enums, start=0) # type: ignore
    return choices
