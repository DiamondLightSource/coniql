from dataclasses import dataclass
from typing import List

from device.motor import Motor
from device.positioner import Positioner
from device.stage3d import Stage3D


@dataclass
class Goniometer:
    omega: Motor
    sample: Stage3D
    chi: Motor
    phi: Motor
