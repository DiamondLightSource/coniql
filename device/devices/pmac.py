from dataclasses import dataclass
from typing import Optional, List, Generator, \
    Tuple, Generic, TypeVar

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel
from device.devices.motor import Motor
from device.pmacutil.pmacconst import CS_AXIS_NAMES


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
    positions: ReadOnlyChannel[List[float]]


T = TypeVar('T')


@dataclass
class CsAxisMapping(Generic[T]):
    a: T
    b: T
    c: T
    u: T
    v: T
    w: T
    x: T
    y: T
    z: T

    def __getitem__(self, item: str):
        # TODO: Should be case sensitive
        item = item.lower()
        names = [c.lower() for c in CS_AXIS_NAMES]
        if item in names:
            return self.__dict__[item]
        else:
            raise KeyError(f'{item} not a valid CS axis')


@dataclass
class Axes(CsAxisMapping[Axis]):
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
class AxisMotors:
    a: Optional[Motor] = doc_field("axis a", None)
    b: Optional[Motor] = doc_field("axis b", None)
    c: Optional[Motor] = doc_field("axis c", None)
    u: Optional[Motor] = doc_field("axis u", None)
    v: Optional[Motor] = doc_field("axis v", None)
    w: Optional[Motor] = doc_field("axis w", None)
    x: Optional[Motor] = doc_field("axis x", None)
    y: Optional[Motor] = doc_field("axis y", None)
    z: Optional[Motor] = doc_field("axis z", None)

    def __getitem__(self, item):
        return self.__dict__[item]

    def available_axes(self) -> Generator[Tuple[str, Motor], None, None]:  # TODO: Temporary to work with pmaac child part
        for name, motor in self.__dict__.items():
            if motor is not None:
                yield name, motor


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
    coordinate_system_name: ReadWriteChannel[str]

    profile_build: ProfileBuild
    points_append: ProfilePart
    profile_execution: ProfilePart

    axes: Axes
    axis_motors: AxisMotors  # TODO: Better separation!

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


@dataclass
class Pmac:
    trajectory: PmacTrajectory
    i10: ReadOnlyChannel[int]

    async def servo_frequency(self) -> float:
        i10 = await self.i10.get()
        return 8388608000.0 / i10

    async def layout(self):
        return
