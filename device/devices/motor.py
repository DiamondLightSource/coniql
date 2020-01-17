from dataclasses import dataclass

from device.devices.joggable import Joggable
from device.devices.limitable import MaxLimitable, MinLimitable
from device.devices.pidcontroller import PidController
from device.devices.positioner import Positioner
from device.devicetypes.channel import ReadWriteChannel


@dataclass
class Motor(Positioner, Joggable, PidController, MinLimitable, MaxLimitable):
    velocity: ReadWriteChannel[float]
