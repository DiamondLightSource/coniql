from dataclasses import dataclass

from device.motor.motor import Motor


@dataclass
class Stage3D:
    x: Motor
    y: Motor
    z: Motor

    def iterator(self):
        return [self.x, self.y, self.z]
