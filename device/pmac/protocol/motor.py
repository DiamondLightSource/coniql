from typing_extensions import Protocol

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadWriteChannel
from device.motor.protocol.scannable import ScannableMotor


class PmacMotor(ScannableMotor, Protocol):
    cs_port: ReadWriteChannel[str] = doc_field(
        "Coordinate system port of this motor")
    cs_axis: ReadWriteChannel[str] = doc_field(
        "Coordinate system axis of this motor")
