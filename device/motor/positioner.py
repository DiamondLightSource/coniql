from dataclasses import dataclass

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadOnlyChannel, ReadWriteChannel


@dataclass
class Positioner:
    """Abstract representation of a device that minimises error between a
    setpoint and an indicated position e.g. a motor or temperature controller"""
    position: ReadOnlyChannel[float] = doc_field(
        "The current indicated position")
    setpoint: ReadWriteChannel[float] = doc_field(
        "The target position")


@dataclass
class PositionerWithStatus(Positioner):
    stationary: ReadOnlyChannel[bool] = doc_field(
        "True if the positioner is not currently adjusting to minimize error")
