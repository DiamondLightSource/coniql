# Treat all division as float division even in python2
from __future__ import division

from typing import Dict

import numpy as np
from annotypes import TYPE_CHECKING
from scanpointgenerator import Point

# from malcolm.core import Context
# from malcolm.modules import builtin, scanning
# from .infos import MotorInfo
from device.pmac.motorinfo import MotorInfo
from device.scanutil.scanningutil import MotionTrigger

if TYPE_CHECKING:
    from typing import Dict, List

    Profiles = Dict[str, List[float]]


def point_velocities(axis_mapping, point, entry=True):
    # type: (Dict[str, MotorInfo], Point, bool) -> Dict[str, float]
    """Find the velocities of each axis over the entry/exit of current point"""
    velocities = {}
    for axis_name, motor_info in axis_mapping.items():
        #            x
        #        x       x
        #    x               x
        #    vl  vlp vp  vpu vu
        # Given distances from point,lower, position, upper, calculate
        # velocity at entry (vl) or exit (vu) of point by extrapolation
        dp = point.upper[axis_name] - point.lower[axis_name]
        vp = dp / point.duration
        if entry:
            # Halfway point is vlp, so calculate dlp
            d_half = point.positions[axis_name] - point.lower[axis_name]
        else:
            # Halfway point is vpu, so calculate dpu
            d_half = point.upper[axis_name] - point.positions[axis_name]
        # Extrapolate to get our entry or exit velocity
        # (vl + vp) / 2 = vlp
        # so vl = 2 * vlp - vp
        # where vlp = dlp / (t/2)
        velocity = 4 * d_half / point.duration - vp
        assert abs(velocity) < motor_info.max_velocity, \
            "Velocity %s invalid for %r with max_velocity %s" % (
                velocity, axis_name, motor_info.max_velocity)
        velocities[axis_name] = velocity
    return velocities


AxisProfileArrays = Dict[str, np.ndarray]


def get_motion_trigger(part_info):
    # type: (scanning.hooks.APartInfo) -> scanning.infos.MotionTrigger
    # infos = MotionTriggerInfo.filter_values(part_info)
    # if infos:
    #     assert len(infos) == 1, \
    #         "Expected 0 or 1 MotionTriggerInfo, got %d" % len(infos)
    #     trigger = infos[0].trigger
    # else:
    #     trigger = MotionTrigger.EVERY_POINT
    # return trigger
    return MotionTrigger.EVERY_POINT
