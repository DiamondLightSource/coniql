from dataclasses import dataclass

from device.devices.motor import Motor, PmacMotor


@dataclass
class TomoStage:
    x: PmacMotor
    theta: PmacMotor
