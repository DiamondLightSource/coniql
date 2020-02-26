import asyncio
from typing import Optional

import numpy as np

from device.devices.pmac import Pmac, Axis, PmacTrajectory
# expected trajectory program number
from device.pmacutil.profile import PmacTrajectoryProfile

TRAJECTORY_PROGRAM_NUM = 2

# The maximum number of points in a single trajectory scan
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
        action = traj.build_profile()
        await asyncio.wait([
            profile_build.max_points.put(MAX_NUM_POINTS),
            traj.coordinate_system_name.put(cs_port)
        ])
    else:
        # This is an append
        action = traj.append_points()

    await write_arrays(pmac, profile)

    # Write the profile
    await action


async def ensure_correct_trajectory_program(traj: PmacTrajectory):
    """make sure a matching trajectory program is installed on the pmac
    """
    program_version = await traj.program_version.get()
    assert program_version == TRAJECTORY_PROGRAM_NUM, \
        f'pmac trajectory program {program_version} detected, ' \
        f'conqil requires {TRAJECTORY_PROGRAM_NUM}'


async def write_arrays(pmac: Pmac, profile: PmacTrajectoryProfile):
    profile_build = pmac.trajectory.profile_build

    num_points = len(profile.time_array)
    common_jobs = [profile_build.num_points_to_build.put(num_points),
                   profile_build.time_array.put(profile.time_array),
                   profile_build.velocity_mode.put(profile.velocity_mode),
                   profile_build.user_programs.put(profile.user_programs)]

    axis_demands = zip(pmac.trajectory.axes.iterator(), profile.axes.iterator())
    axis_jobs = [setup_axis(axis, demands)
                 for axis, demands in axis_demands]

    await asyncio.wait(common_jobs + axis_jobs)


async def setup_axis(axis: Axis, demands: np.ndarray):
    if demands:
        await axis.use.put(True)
        await axis.positions.put(demands)
    else:
        await axis.use.put(False)

