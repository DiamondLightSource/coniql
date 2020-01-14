from dataclasses import dataclass

from coniql.util import doc_field
from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel


@dataclass
class PidController:
    """Device with channels permitting control of a PID control loop"""
    p: ReadWriteChannel[float] = doc_field(
        "The proportional gain")
    i: ReadWriteChannel[float] = doc_field(
        "The integral gain")
    d: ReadWriteChannel[float] = doc_field(
        "The derivative gain")
