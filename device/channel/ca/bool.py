from typing_extensions import Protocol

from device.channel.ca.channel import CaChannel


class CaBool(CaChannel[bool]):
    def format_value(self, value) -> bool:
        return bool(value)


