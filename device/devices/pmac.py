import asyncio
import numpy as np

from dataclasses import dataclass
from typing import Optional, Any, List, Dict, TypeVar, Generic, Set, Generator, \
    Tuple

from coniql.util import doc_field
from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel
from device.devices.motor import Motor
from device.pmacutil.velocityprofile import VelocityArrays


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


@dataclass
class Axis:
    use: ReadWriteChannel[bool]
    num_points: ReadOnlyChannel[int]
    max_points: ReadOnlyChannel[int]


@dataclass
class Axes:
    a: Axis = doc_field("axis a")
    b: Axis = doc_field("axis b")
    c: Axis = doc_field("axis c")
    u: Axis = doc_field("axis u")
    v: Axis = doc_field("axis v")
    w: Axis = doc_field("axis w")
    x: Axis = doc_field("axis x")
    y: Axis = doc_field("axis y")
    z: Axis = doc_field("axis z")


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


# expected trajectory program number
TRAJECTORY_PROGRAM_NUM = 2

# The maximum number of points in a single trajectory scan
MAX_NUM_POINTS = 4000000


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

    async def write_profile(self, time_array: List[float],
                            velocity_array: List[float],
                            axes: Dict[str, int],
                            cs_port: Optional[str] = None, velocity_mode=None,
                            user_programs=None):
        # make sure a matching trajectory program is installed on the pmac
        # if child.trajectoryProgVersion.value != TRAJECTORY_PROGRAM_NUM:
        #     raise (
        #         IncompatibleError(
        #             "pmac trajectory program {} detected. "
        #             "Malcolm requires {}".format(
        #                 child.trajectoryProgVersion.value,
        #                 TRAJECTORY_PROGRAM_NUM
        #             )
        #         )
        #     ) TODO: Add channels for this

        # The axes taking part in the scan
        # use_axes = []
        # for axis in CS_AXIS_NAMES:
        #     if locals()[axis.lower()] is not None:
        #         use_axes.append(axis)
        # time_array, velocity_array = arrays
        use_axes = {self.axes.__dict__[axis_name]: n for axis_name, n in
                    axes.keys()}
        if cs_port is not None:
            # This is a build
            action = self.build_profile()
            # self.total_points = 0
            await self.profile_build.max_points.put_value(MAX_NUM_POINTS)
            try:
                self.coordinate_system_name.put_value(cs_port)
            except ValueError as e:
                raise ValueError(
                    "Cannot set CS to %s, did you use a compound_motor_block "
                    "for a raw motor?\n%s" % (cs_port, e))
            await asyncio.wait([axis.use.put(True) for axis in use_axes])
        else:
            # This is an append
            action = self.append_points()

        # Fill in the arrays
        num_points = len(time_array)
        await asyncio.wait([
                               self.profile_build.num_points_to_build.put(
                                   num_points),
                               self.profile_build.time_array.put(time_array),
                               self.profile_build.velocity_mode.put(
                                   _zeros_or_right_length(velocity_mode,
                                                          num_points)),
                               self.profile_build.user_programs.put(
                                   _zeros_or_right_length(user_programs,
                                                          num_points))
                           ] + [
                               axis.max_points.put(max_p) for axis, max_p in
                               use_axes.items()
                           ])
        # Write the profile
        await action
        # Record how many points we have now written in total

        # self.total_points += num_points

    async def build_profile(self):
        await self.profile_build.trigger.put(True)

    async def append_points(self):
        await self.points_append.trigger.put(True)

    async def execute_profile(self):
        await self.profile_execution.trigger.put(True)

    async def abort(self):
        await self.profile_abort.put(False)


def _zeros_or_right_length(array, num_points):
    if array is None:
        array = np.zeros(num_points, np.int32)
    else:
        assert len(array) == num_points, \
            "Array %s should be %d points long" % (
                array, num_points)
    return array


@dataclass
class Pmac:
    trajectory: PmacTrajectory
    i10: ReadOnlyChannel[int]

    async def servo_frequency(self) -> float:
        i10 = (await self.i10.get()).value
        return 8388608000.0 / i10
