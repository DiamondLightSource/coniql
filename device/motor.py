from dataclasses import dataclass

from device.joggable import Joggable
from device.pidcontroller import PidController
from device.positioner import Positioner
from device.types.channel import ReadWriteChannel


@dataclass
class Motor(Positioner, Joggable, PidController):
    velocity: ReadWriteChannel[float]
