from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadWriteChannel


@dataclass
class MaxLimitable:
    max: ReadWriteChannel[float]


@dataclass
class MinLimitable:
    min: ReadWriteChannel[float]
