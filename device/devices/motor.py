import asyncio
from dataclasses import dataclass

from coniql.util import doc_field
from device.devices.joggable import Joggable
from device.devices.limitable import MaxLimitable, MinLimitable
from device.devices.pidcontroller import PidController
from device.devices.positioner import PositionerWithStatus
from device.channel.channeltypes.channel import ReadWriteChannel
from device.pmacutil.pmacconst import CS_AXIS_NAMES
from device.util import get_all_values


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

    cs_port: ReadWriteChannel[str] = doc_field(
        "Coordinate system port of this motor")
    cs_axis: ReadWriteChannel[str] = doc_field(
        "Coordinate system axis of this motor")

    async def cs(self):
        cs_port = (await self.cs_port.get()).value
        cs_axis = (await self.cs_axis.get()).value
        return f'{cs_port},{cs_axis}'
        # value = (await self.output.get()).value
        #
        #
        # split = value.split("(")[1].rstrip(")").split(",")
        # cs_port = split[0].strip()
        # cs_axis = CS_AXIS_NAMES[int(split[1].strip()) - 1]
        # result = "%s,%s" % (cs_port, cs_axis)
        # return result
