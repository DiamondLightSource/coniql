from dataclasses import dataclass

from typing_extensions import Protocol

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadOnlyChannel, ReadWriteChannel


class Positioner(Protocol):
    """Abstract representation of a protocol that minimises error between a
    setpoint and an indicated position e.g. a motor or temperature controller"""
    position: ReadOnlyChannel[float] = doc_field(
        "The current indicated position")
    setpoint: ReadWriteChannel[float] = doc_field(
        "The target position")


class PositionerWithStatus(Positioner, Protocol):
    stationary: ReadOnlyChannel[bool] = doc_field(
        "True if the positioner is not currently adjusting to minimize error")
