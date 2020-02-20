from typing_extensions import Protocol

from device.channel.ca.channel import CaChannel, T


class CaString(CaChannel[str]):
    def format_value(self, value) -> str:
        return str(value)
