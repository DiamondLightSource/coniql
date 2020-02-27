from dataclasses import dataclass

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel
from device.channel.multi import get_all
from device.motor import Motor


@dataclass
class MotorCs:
    port: str
    axis: str

    @classmethod
    def empty(cls):
        return MotorCs('', '')


@dataclass
class PmacMotor(Motor):
    cs_port: ReadWriteChannel[str] = doc_field(
        "Coordinate system port of this motor")
    cs_axis: ReadWriteChannel[str] = doc_field(
        "Coordinate system axis of this motor")

    # TODO: This is only a temporary place to put this.
    #  at some point there should be some sort of scannable map.
    scannable_name: ReadOnlyChannel[str] = doc_field(
        "GDA scannable associated with this motor")

    async def cs(self) -> MotorCs:
        cs_port, cs_axis = await get_all(
            self.cs_port, self.cs_axis)
        return MotorCs(cs_port, cs_axis)