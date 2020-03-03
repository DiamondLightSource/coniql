import asyncio
from typing import Optional

import numpy as np

from device.pmac.modes import CS_AXIS_NAMES
from device.pmac.csaxes import get_axis
from device.pmac.protocol.pmac import Pmac, Trajectory, CsDemands, DemandsAxis
from device.pmac.deviceutil.trajectory import append_points, build_profile
from device.pmac.profile.trajectoryprofile import PmacTrajectoryProfile

TRAJECTORY_PROGRAM_NUM = 2.0

# The maximum number of points in a single control scan
MAX_NUM_POINTS = 4000000


async def write_profile(pmac: Pmac,
                        profile: PmacTrajectoryProfile,
                        cs_port: Optional[str] = None):
    traj = pmac.trajectory
    profile = profile.with_padded_optionals()

    await ensure_correct_trajectory_program(traj)

    profile_build = traj.profile_build
    if cs_port is not None:
        # This is a build
        action = build_profile(traj)
        await asyncio.wait([
            traj.cs_demands.max_points.put(MAX_NUM_POINTS),
            traj.coordinate_system_name.put(cs_port)
        ])
    else:
        # This is an append
        action = append_points(traj)

    await write_arrays(pmac, profile)

    # Write the profile
    await action


async def ensure_correct_trajectory_program(traj: Trajectory):
    """make sure a matching control program is installed on the pmac
    """
    program_version = await traj.program_version.get()
    assert float(program_version) == TRAJECTORY_PROGRAM_NUM, \
        f'pmac control program {program_version} detected, ' \
        f'conqil requires {TRAJECTORY_PROGRAM_NUM}'


async def write_arrays(pmac: Pmac, profile: PmacTrajectoryProfile):
    traj = pmac.trajectory
    cs_demands = traj.cs_demands
    profile_build = traj.profile_build

    num_points = len(profile.time_array)
    common_jobs = [cs_demands.num_points_to_build.put(num_points),
                   cs_demands.time_array.put(profile.time_array),
                   cs_demands.velocity_mode.put(profile.velocity_mode),
                   cs_demands.user_programs.put(profile.user_programs)]

    axis_demands = ((get_axis(cs_demands, axis), profile[axis])
                    for axis in CS_AXIS_NAMES)
    # axis_demands = zip(cs_demands.iterator(), profile.axes.iterator())
    axis_jobs = [setup_axis(axis, demands)
                 for axis, demands in axis_demands]

    await asyncio.wait(common_jobs + axis_jobs)


async def setup_axis(axis: DemandsAxis, demands: np.ndarray):
    if demands:
        await axis.use.put(True)
        await axis.positions.put(demands)
    else:
        await axis.use.put(False)
