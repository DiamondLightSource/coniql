from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadWriteChannel


@dataclass
class Bits:
    """Soft inputs and constant bits"""
    a: ReadWriteChannel[bool]
    b: ReadWriteChannel[bool]
    c: ReadWriteChannel[bool]
    d: ReadWriteChannel[bool]


@dataclass
class Panda:
    bits: Bits
