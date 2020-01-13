from dataclasses import dataclass

from device.joggable import Joggable
from device.pidcontroller import PidController
from device.positioner import Positioner


@dataclass
class Motor(Positioner, Joggable, PidController):
    pass
