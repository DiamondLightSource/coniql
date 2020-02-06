from dataclasses import dataclass

from coniql.util import doc_field
from device.devices.joggable import Joggable
from device.devices.limitable import MaxLimitable, MinLimitable
from device.devices.pidcontroller import PidController
from device.devices.positioner import PositionerWithStatus
from device.channel.channeltypes.channel import ReadWriteChannel


@dataclass
class Motor(PositionerWithStatus, Joggable, PidController, MinLimitable, MaxLimitable):
    velocity: ReadWriteChannel[float] = doc_field("Velocity of the motor")
    max_velocity: ReadWriteChannel[float] = doc_field("Velocity limit of the "
                                                      "motor")
