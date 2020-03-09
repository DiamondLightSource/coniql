from typing_extensions import Protocol

from device.channel.ca.channel import CaChannel


class CaBool(CaChannel[bool]):
    """A channel representing a channel access bool. Can be used to convert
    channels that store int 0 or 1 to explicit Python bools."""
    def format_value(self, value) -> bool:
        return bool(value)


