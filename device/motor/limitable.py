from dataclasses import dataclass

from typing_extensions import Protocol

from device.channel.channeltypes.channel import ReadWriteChannel


class MaxLimitable(Protocol):
    max: ReadWriteChannel[float]


class MinLimitable(Protocol):
    min: ReadWriteChannel[float]
