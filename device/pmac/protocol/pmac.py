from typing import List

from typing_extensions import Protocol

from device.channel.channeltypes.channel import ReadOnlyChannel, \
    ReadWriteChannel
from device.pmac.csaxes import CsAxes


class DemandsAxis(Protocol):
    use: ReadWriteChannel[bool]
    num_points: ReadWriteChannel[int]
    max_points: ReadWriteChannel[int]
    positions: ReadWriteChannel[List[float]]


class CsDemands(CsAxes[DemandsAxis], Protocol):
    time_array: ReadWriteChannel[List[float]]
    velocity_mode: ReadWriteChannel[List[int]]
    user_programs: ReadWriteChannel[List[int]]
    max_points: ReadWriteChannel[int]
    num_points_to_build: ReadWriteChannel[int]


class ProfilePart(Protocol):
    trigger: ReadWriteChannel[str]
    status: ReadOnlyChannel[str]
    state: ReadOnlyChannel[str]
    message: ReadOnlyChannel[str]


class Trajectory(Protocol):
    cs_demands: CsDemands
    profile_build: ProfilePart
    program_version: ReadOnlyChannel[str]
    coordinate_system_name: ReadWriteChannel[str]

    async def build_profile(self):
        await self.profile_build.trigger.put('Build')

    async def append_points(self):
        await self.points_append.trigger.put('Append')

    async def execute_profile(self):
        await self.profile_execution.trigger.put('Execute')

    async def abort(self):
        await self.profile_abort.put(False)


class Pmac(Protocol):
    i10: ReadOnlyChannel[int]
    motors: ReadOnlyChannel[List[str]]
    trajectory: Trajectory

    async def servo_frequency(self) -> float:
        i10 = await self.i10.get()
        return 8388608000.0 / i10

    async def layout(self):
        return NotImplemented

