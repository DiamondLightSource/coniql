from dataclasses import dataclass

from device.devicetypes.channel import ReadWriteChannel


@dataclass
class MaxLimitable:
    max: ReadWriteChannel[float]


@dataclass
class MinLimitable:
    min: ReadWriteChannel[float]
