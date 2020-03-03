from dataclasses import dataclass

from device.pmac.protocol.motor import PmacMotor


@dataclass
class TomoStage:
    x: PmacMotor
    theta: PmacMotor
