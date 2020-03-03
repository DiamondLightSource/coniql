from dataclasses import dataclass

from typing_extensions import Protocol

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadWriteChannel


class PidController(Protocol):
    """Device with channels permitting control of a PID control loop"""
    p: ReadWriteChannel[float] = doc_field(
        "The proportional gain")
    i: ReadWriteChannel[float] = doc_field(
        "The integral gain")
    d: ReadWriteChannel[float] = doc_field(
        "The derivative gain")
