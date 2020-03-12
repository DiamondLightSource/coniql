from typing_extensions import Protocol

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadOnlyChannel
from device.motor.protocol.motor import Motor


class ScannableMotor(Motor, Protocol):
    scannable_name: ReadOnlyChannel[str] = doc_field(
        "GDA scannable associated with this motor")
