from dataclasses import dataclass

from typing_extensions import Protocol

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadWriteChannel
from device.motor.joggable import Joggable
from device.motor.limitable import MaxLimitable, MinLimitable
from device.motor.pidcontroller import PidController
from device.motor.positioner import PositionerWithStatus


class Motor(PositionerWithStatus, Joggable, PidController, MinLimitable,
            MaxLimitable, Protocol):
    velocity: ReadWriteChannel[float] = doc_field("Velocity of the motor")
    max_velocity: ReadWriteChannel[float] = doc_field("Velocity limit of the "
                                                      "motor")
    acceleration_time: ReadWriteChannel[float] = doc_field("Time to reach "
                                                           "max_velocity")
    output: ReadWriteChannel[str] = doc_field("Output specification, "
                                              "freeform string")
    resolution: ReadWriteChannel[float] = doc_field("Resolution of this motor")
    offset: ReadWriteChannel[float] = doc_field("User-defined offset")
    units: ReadWriteChannel[str] = doc_field("Engineering units used by "
                                             "this record")
