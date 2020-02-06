from dataclasses import dataclass

from device.devices.motor import Motor


@dataclass
class TomoStage:
    x: Motor
    theta: Motor
