from dataclasses import dataclass

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadWriteChannel
from device.channel.multi import get_all
from device.devices.joggable import Joggable
from device.devices.limitable import MaxLimitable, MinLimitable
from device.devices.pidcontroller import PidController
from device.devices.positioner import PositionerWithStatus


@dataclass
class Motor(PositionerWithStatus, Joggable, PidController, MinLimitable,
            MaxLimitable):
    velocity: ReadWriteChannel[float] = doc_field("Velocity of the motor")
    max_velocity: ReadWriteChannel[float] = doc_field("Velocity limit of the "
                                                      "motor")
    acceleration_time: ReadWriteChannel[float] = doc_field("Time to reach "
                                                           "max_velocity")
    output: ReadWriteChannel[str] = doc_field("Output specification, "
                                              "freeform string")
    resolution: ReadWriteChannel[float] = doc_field("Resolution of this motor")
    offset: ReadWriteChannel[float] = doc_field("User-defined offset")
    units: ReadWriteChannel[str] = doc_field("Engineering units used by "
                                             "this record")


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

    async def cs(self) -> MotorCs:
        cs_port, cs_axis = await get_all(
            self.cs_port, self.cs_axis)
        return MotorCs(cs_port, cs_axis)
