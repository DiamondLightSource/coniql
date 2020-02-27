from dataclasses import dataclass

from device.motor import Motor


@dataclass
class Stage3D:
    x: Motor
    y: Motor
    z: Motor
