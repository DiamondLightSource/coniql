from typing_extensions import Protocol
from dataclasses import dataclass

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadOnlyChannel
from device.motor.motor import Motor


class ScannableMotor(Motor, Protocol):
    # TODO: This is only a temporary place to put this.
    #  at some point there should be some sort of scannable map.
    scannable_name: ReadOnlyChannel[str] = doc_field(
        "GDA scannable associated with this motor")
