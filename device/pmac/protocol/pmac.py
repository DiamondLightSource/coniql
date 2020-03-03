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
    points_append: ProfilePart
    profile_execution: ProfilePart
    program_version: ReadOnlyChannel[str]
    coordinate_system_name: ReadWriteChannel[str]
    profile_abort: ReadWriteChannel[bool]


class Pmac(Protocol):
    i10: ReadOnlyChannel[int]
    motors: ReadOnlyChannel[List[str]]
    trajectory: Trajectory

