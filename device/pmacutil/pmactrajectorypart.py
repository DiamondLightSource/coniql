import asyncio
from typing import List, Optional, Dict

import numpy as np

from device.devices.pmac import Pmac

# expected trajectory program number
TRAJECTORY_PROGRAM_NUM = 2

# The maximum number of points in a single trajectory scan
MAX_NUM_POINTS = 4000000


class PmacTrajectoryPart:
    def __init__(self, pmac: Pmac):
        self.pmac = pmac

    async def write_profile(self,
                            time_array: List[float],
                            velocity_array: Optional[List[float]] = None,
                            cs_port: Optional[str] = None, velocity_mode=None,
                            user_programs=None,
                            positions: Optional[Dict[str, List[float]]] = None):
        traj = self.pmac.trajectory
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
        positions = positions or {}
        use_axes = {traj.axes[axis_name]: n for axis_name, n in
                    positions.items()}
        # use_axes = [self.axes.__dict__[axis_name] for axis_name in positions.keys()]
        if cs_port is not None:
            # This is a build
            action = traj.build_profile()
            # self.total_points = 0
            await traj.profile_build.max_points.put(MAX_NUM_POINTS)
            try:
                await traj.coordinate_system_name.put(cs_port)
            except ValueError as e:
                raise ValueError(
                    "Cannot set CS to %s, did you use a compound_motor_block "
                    "for a raw motor?\n%s" % (cs_port, e))
            jobs = [axis.use.put(True) for axis in use_axes.keys()]
            if jobs:
                await asyncio.wait(jobs)
        else:
            # This is an append
            action = traj.append_points()

        # Fill in the arrays
        num_points = len(time_array)
        await asyncio.wait([
                               traj.profile_build.num_points_to_build.put(
                                   num_points),
                               traj.profile_build.time_array.put(time_array),
                               traj.profile_build.velocity_mode.put(
                                   _zeros_or_right_length(velocity_mode,
                                                          num_points)),
                               traj.profile_build.user_programs.put(
                                   _zeros_or_right_length(user_programs,
                                                          num_points))
                           ]
                           + [
                               axis.positions.put(positions) for axis, positions
                               in
                               use_axes.items()
                           ])
        # Write the profile
        await action
        # Record how many points we have now written in total

        # self.total_points += num_points


def _zeros_or_right_length(array, num_points):
    if array is None:
        array = np.zeros(num_points, np.int32)
    else:
        assert len(array) == num_points, \
            "Array %s should be %d points long" % (
                array, num_points)
    return array
