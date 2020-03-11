from typing_extensions import Protocol

from device.channel.channeltypes.channel import ReadWriteChannel


class FastShutter(Protocol):
    mode: ReadWriteChannel[str]
    status: ReadWriteChannel[str]
