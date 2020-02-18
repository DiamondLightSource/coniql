from enum import IntEnum, EnumMeta
from typing import Optional

import aioca

from device.channel.ca.channel import CaChannel, CaField
from device.channel.channeltypes.channel import DEFAULT_TIMEOUT
from device.channel.channeltypes.result import Readback


class CaString(CaField):
    async def create_channel(self) -> 'CaStringChannel':
        return CaStringChannel(self.pv, self.rbv, self.wait,self.timeout)


class CaStringChannel(CaChannel[str]):
    def format_value(self, value):
        return str(value)
