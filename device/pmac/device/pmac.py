from dataclasses import dataclass
from typing import List, Iterable

from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel
from device.pmac.device.motor import PmacMotor
from device.pmac.csaxes import CsAxes


@dataclass
class ProfilePart:
    trigger: ReadWriteChannel[bool]
    status: ReadOnlyChannel[str]
    state: ReadOnlyChannel[str]
    message: ReadOnlyChannel[str]


@dataclass
class ProfileBuild(ProfilePart):
    max_points: ReadWriteChannel[int]
    num_points_to_build: ReadWriteChannel[int]

    time_array: ReadWriteChannel[List[float]]
    velocity_mode: ReadWriteChannel[List[int]]
    user_programs: ReadWriteChannel[List[int]]


@dataclass(unsafe_hash=True)
class Axis:
    use: ReadWriteChannel[bool]
    num_points: ReadOnlyChannel[int]
    max_points: ReadOnlyChannel[int]
    positions: ReadWriteChannel[List[float]]


@dataclass
class Axes(CsAxes[Axis]):
    pass
    # a: Axis = doc_field("axis a")
    # b: Axis = doc_field("axis b")
    # c: Axis = doc_field("axis c")
    # u: Axis = doc_field("axis u")
    # v: Axis = doc_field("axis v")
    # w: Axis = doc_field("axis w")
    # x: Axis = doc_field("axis x")
    # y: Axis = doc_field("axis y")
    # z: Axis = doc_field("axis z")


@dataclass
class TrajectoryScanStatus:
    buffer_a_address: ReadOnlyChannel[int]
    buffer_b_address: ReadOnlyChannel[int]
    num_points_in_buffer: ReadOnlyChannel[int]
    current_buffer: ReadOnlyChannel[str]
    current_index: ReadOnlyChannel[int]
    points_scanned: ReadOnlyChannel[int]
    status: ReadOnlyChannel[str]


@dataclass
class TrajDriverStatus:
    driver_a_index: ReadOnlyChannel[int]
    driver_b_index: ReadOnlyChannel[int]
    num_points_in_scan: ReadOnlyChannel[int]
    scan_time: ReadOnlyChannel[float]
    coordinate_system: ReadOnlyChannel[int]
    status: ReadOnlyChannel[str]


@dataclass
class PmacTrajectory:
    program_version: ReadOnlyChannel[float]

    coordinate_system_name: ReadWriteChannel[str]

    profile_build: ProfileBuild
    points_append: ProfilePart
    profile_execution: ProfilePart

    axes: Axes
    # axis_motors: AxisMotors  # TODO: Better separation!

    scan_status: TrajectoryScanStatus
    driver_status: TrajDriverStatus

    percentage_complete: ReadOnlyChannel[float]
    profile_abort: ReadOnlyChannel[bool]

    async def build_profile(self):
        await self.profile_build.trigger.put('Build')

    async def append_points(self):
        await self.points_append.trigger.put('Append')

    async def execute_profile(self):
        await self.profile_execution.trigger.put('Execute')

    async def abort(self):
        await self.profile_abort.put(False)

# CsAxisMapping = Dict[CsAxis, PmacMotor]
# CsAxisMappings = Dict[str, CsAxisMapping]


@dataclass
class PmacMotors:
    axis_1: PmacMotor
    axis_2: PmacMotor

    def iterator(self) -> Iterable[PmacMotor]:
        return [self.axis_1, self.axis_2]

    # async def cs_axis_mappings(self) -> CsAxisMappings:
    #     mappings: CsAxisMappings = {}
    #     for motor in self.iterator():
    #         cs = await motor.cs()
    #         if cs.port not in mappings:
    #             mappings[cs.port] = {}
    #         mappings[cs.port][cs.axis] = motor
    #     return mappings


@dataclass
class Pmac:
    trajectory: PmacTrajectory
    motors: PmacMotors

    i10: ReadOnlyChannel[int]

    async def servo_frequency(self) -> float:
        i10 = await self.i10.get()
        return 8388608000.0 / i10

    async def layout(self):
        return NotImplemented
