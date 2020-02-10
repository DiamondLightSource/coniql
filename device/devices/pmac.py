from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel


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


@dataclass
class Axis:
    use: ReadWriteChannel[bool]
    num_points: ReadOnlyChannel[int]
    max_points: ReadOnlyChannel[int]


@dataclass
class Axes:
    a: Axis
    b: Axis
    c: Axis
    u: Axis
    v: Axis
    w: Axis
    x: Axis
    y: Axis
    z: Axis


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

    scan_status: TrajectoryScanStatus
    driver_status: TrajDriverStatus

    percentage_complete: ReadOnlyChannel[float]
    profile_abort: ReadOnlyChannel[bool]

    def build_profile(self):
        await self.profile_build.trigger.put(True)

    def append_points(self):
        await self.points_append.trigger.put(True)

    def execute_profile(self):
        await self.profile_execution.trigger.put(True)

    def abort(self):
        await self.profile_abort.put(False)


@dataclass
class Pmac:
    trajectory: PmacTrajectory
