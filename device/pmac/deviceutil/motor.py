from dataclasses import dataclass

from device.channel.multi import get_all
from device.pmac.protocol.motor import PmacMotor


@dataclass
class MotorCs:
    port: str
    axis: str

    @classmethod
    def empty(cls):
        return MotorCs('', '')


async def coordinate_system(motor: PmacMotor) -> MotorCs:
    cs_port, cs_axis = await get_all(
        motor.cs_port, motor.cs_axis)
    return MotorCs(cs_port, cs_axis)
