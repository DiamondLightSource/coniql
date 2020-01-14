from dataclasses import dataclass

from device.devices.motor import Motor
from device.devices.stage3d import Stage3D


@dataclass
class Goniometer:
    omega: Motor
    sample: Stage3D
    chi: Motor
    phi: Motor
