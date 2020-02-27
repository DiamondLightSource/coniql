from dataclasses import dataclass

from device.pmac.device.motor import PmacMotor


@dataclass
class TomoStage:
    x: PmacMotor
    theta: PmacMotor
