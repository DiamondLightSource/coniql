from dataclasses import dataclass

from typing_extensions import Protocol

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel
from device.channel.multi import get_all
from device.motor.motor import Motor
from device.motor.scannable import ScannableMotor


@dataclass
class MotorCs:
    port: str
    axis: str

    @classmethod
    def empty(cls):
        return MotorCs('', '')


class PmacMotor(ScannableMotor, Protocol):
    cs_port: ReadWriteChannel[str] = doc_field(
        "Coordinate system port of this motor")
    cs_axis: ReadWriteChannel[str] = doc_field(
        "Coordinate system axis of this motor")

    async def cs(self) -> MotorCs:
        cs_port, cs_axis = await get_all(
            self.cs_port, self.cs_axis)
        return MotorCs(cs_port, cs_axis)