from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadWriteChannel


@dataclass
class FastShutter:
    mode: ReadWriteChannel[int]
    status: ReadWriteChannel[int]
    # TODO: Aha! A channel that can sometimes be mutable
