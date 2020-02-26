import asyncio
from typing import List, Optional, Dict

import numpy as np

from device.devices.pmac import Pmac, Axes, PmacTrajectory, ProfileBuild, Axis

# expected trajectory program number
from device.pmacutil.pmacconst import CS_AXIS_NAMES
from device.pmacutil.profile import PmacTrajectoryProfile

TRAJECTORY_PROGRAM_NUM = 2

# The maximum number of points in a single trajectory scan
MAX_NUM_POINTS = 4000000


async def write_profile(pmac: Pmac,
                        profile: PmacTrajectoryProfile,
                        cs_port: Optional[str] = None):
    traj = pmac.trajectory
    profile = profile.with_padded_optionals()

    # make sure a matching trajectory program is installed on the pmac
    program_version = await traj.program_version.get()
    assert program_version == TRAJECTORY_PROGRAM_NUM, \
        f'pmac trajectory program {program_version} detected, ' \
        f'conqil requires {TRAJECTORY_PROGRAM_NUM}'

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

    await traj.write_profile(profile)

    # Write the profile
    await action


async def setup_axis(axis: Axis, demands: np.ndarray):
    if demands:
        await axis.use.put(True)
        await axis.positions.put(demands)
    else:
        await axis.use.put(False)

