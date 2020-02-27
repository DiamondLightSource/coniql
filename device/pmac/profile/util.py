from typing import Dict, Tuple

import numpy as np
from scanpointgenerator import Point

from device.pmac.modes import PointType, UserProgram, MIN_TIME, MIN_INTERVAL
from device.pmac.motorinfo import MotorInfo
from device.pmac.util import AxisProfileArrays, point_velocities
from device.scanutil.scanningutil import MotionTrigger


def points_joined(axis_mapping, point, next_point):
    # type: (Dict[str, MotorInfo], Point, Point) -> bool
    """Check for axes that need to move within the space between points"""
    if getattr(point, "delay_after", None):
        return False
    for axis_name in axis_mapping:
        if point.upper[axis_name] != next_point.lower[axis_name]:
            return False

    return True


def get_user_program(output_triggers: MotionTrigger,
                     point_type: PointType) -> UserProgram:
    if output_triggers == MotionTrigger.NONE:
        # Always produce no program
        return UserProgram.NO_PROGRAM
    elif output_triggers == MotionTrigger.ROW_GATE:
        if point_type == PointType.START_OF_ROW:
            # Produce a gate for the whole row
            return UserProgram.LIVE_PROGRAM
        elif point_type == PointType.END_OF_ROW:
            # Falling edge of row gate
            return UserProgram.ZERO_PROGRAM
        else:
            # Otherwise don't change anything
            return UserProgram.NO_PROGRAM
    else:
        if point_type in (PointType.START_OF_ROW, PointType.POINT_JOIN):
            return UserProgram.LIVE_PROGRAM
        elif point_type == PointType.END_OF_ROW:
            return UserProgram.DEAD_PROGRAM
        elif point_type == PointType.MID_POINT:
            return UserProgram.MID_PROGRAM
        else:
            return UserProgram.ZERO_PROGRAM


def profile_between_points(
        axis_mapping: Dict[str, MotorInfo],
        point: Point,
        next_point: Point,
        min_time: float = MIN_TIME,
        min_interval: float = MIN_INTERVAL
) -> Tuple[AxisProfileArrays, AxisProfileArrays]:
    """Make consistent time and velocity arrays for each axis
    Try to create velocity profiles for all axes that all arrive at
    'distance' in the same time period. The profiles will contain the
    following points:-
    in the following description acceleration can be -ve or +ve depending
    on the relative sign of v1 and v2. fabs(vm) is <= maximum velocity
    - start point at 0 secs with velocity v1     start accelerating
    - middle velocity start                      reached speed vm
    - middle velocity end                        start accelerating
    - end point with velocity v2                 reached target speed
    Time at vm may be 0 in which case there are only 3 points and
    acceleration to v2 starts as soon as vm is reached.
    If the profile has to be stretched to achieve min_time then the
    the middle period at speed vm is extended accordingly.
    After generating all the profiles this function checks to ensure they
    have all achieved min_time. If not min_time is reset to the slowest
    profile and all profiles are recalculated.
    Note that for each profile the area under the velocity/time plot
    must equal 'distance'. The class VelocityProfile implements the math
    to achieve this.
    """
    start_velocities = point_velocities(axis_mapping, point)
    end_velocities = point_velocities(axis_mapping, next_point, entry=False)

    p = None
    new_min_time = 0
    time_arrays = {}
    velocity_arrays = {}
    profiles = {}
    # The first iteration reveals the slowest profile. The second generates
    # all profiles with the slowest min_time
    iterations = 2
    while iterations > 0:
        for axis_name, motor_info in axis_mapping.items():
            distance = next_point.lower[axis_name] - point.upper[axis_name]
            p = motor_info.make_velocity_profile(
                start_velocities[axis_name], end_velocities[axis_name],
                distance, min_time, min_interval
            )
            # Absolute time values that we are at that velocity
            profiles[axis_name] = p
            new_min_time = max(new_min_time, p.t_total)
        if np.isclose(new_min_time, min_time):
            # We've got our consistent set - see if they require quantization
            quantize = False
            for axis_name, _ in axis_mapping.items():
                quantize = quantize or profiles[axis_name].check_quantize()
            for axis_name, _ in axis_mapping.items():
                if quantize:
                    profiles[axis_name].quantize()
                time_arrays[axis_name], velocity_arrays[axis_name] = \
                    profiles[axis_name].make_arrays()
            return time_arrays, velocity_arrays
        else:
            min_time = new_min_time
            iterations -= 1
    raise ValueError("Can't get a consistent time in 2 iterations")