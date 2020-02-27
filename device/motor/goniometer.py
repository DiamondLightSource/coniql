from dataclasses import dataclass

from device.motor import Motor
from device.motor.stage3d import Stage3D


@dataclass
class Goniometer:
    omega: Motor
    sample: Stage3D
    chi: Motor
    phi: Motor
