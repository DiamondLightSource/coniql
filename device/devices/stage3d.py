from dataclasses import dataclass

from device.devices.motor import Motor


@dataclass
class Stage3D:
    x: Motor
    y: Motor
    z: Motor
