from dataclasses import dataclass
from typing import List, Optional, Dict

import numpy as np

from device.pmac.csaxes import CsAxes
from device.pmac.modes import MIN_TIME, VelocityMode, UserProgram, \
    PointType, CS_AXIS_NAMES
from device.pmac.util import AxisProfileArrays, point_velocities
from device.pmac.profile.util import points_joined, get_user_program, \
    profile_between_points
from device.pmac.motorinfo import MotorInfo
from device.pmac.control.trajectorymodel import TrajectoryModel
from device.scan.util import MotionTrigger

# Longest move time we can request
MAX_MOVE_TIME = 4.0


# How many profile points to write each time
PROFILE_POINTS = 10000


TICK_S = 0.000001


def empty_axis_demands() -> Dict[str, List[float]]:
    return {cs: [] for cs in CS_AXIS_NAMES}


@dataclass
class PmacTrajectoryProfile:
    time_array: List[float]  # of floats
    axes: Dict[str, List[float]]
    user_programs: Optional[List[UserProgram]] = None  # of ints
    velocity_mode: Optional[List[VelocityMode]] = None  # of floats

    @classmethod
    def empty(cls):
        axes = empty_axis_demands()
        return PmacTrajectoryProfile(time_array=[], axes=axes,
                                     user_programs=[], velocity_mode=[])

    def __getitem__(self, item):
        return self.axes[item]

    def in_use(self, axis_name: str) -> bool:
        """Returns True if there are any points to be appended to the
        specified axis"""
        return bool(self[axis_name])

    def num_points(self):
        return len(self.time_array)

    def with_padded_optionals(self):
        num_points = self.num_points()
        user_programs = _zeros_or_right_length(self.user_programs, num_points)
        velocity_mode = _zeros_or_right_length(self.velocity_mode, num_points)
        return PmacTrajectoryProfile(
            time_array=self.time_array,
            user_programs=user_programs,
            velocity_mode=velocity_mode,
            axes=self.axes
        )

    def with_ticks(self):
        overflow = 0.0
        time_array_ticks = []
        for t in self.time_array:
            ticks = t / TICK_S
            overflow += (ticks % 1)
            ticks = int(ticks)
            if overflow > 0.5:
                overflow -= 1
                ticks += 1
            time_array_ticks.append(ticks)
        # TODO: overflow discarded overy 10000 points, is it a problem?
        # profile.time_array = time_array_ticks  # np.array(time_array_ticks, np.int32)
        return PmacTrajectoryProfile(
            time_array=time_array_ticks,
            user_programs=self.user_programs,
            velocity_mode=self.velocity_mode,
            axes=self.axes
        )


def _zeros_or_right_length(array, num_points):
    if array is None:
        array = np.zeros(num_points, np.int32)
    else:
        assert len(array) == num_points, \
            "Array %s should be %d points long" % (
                array, num_points)
    return array


class ProfileGenerator:
    def __init__(self,
                 model: TrajectoryModel,
                 output_triggers: MotionTrigger,
                 axis_mapping: Dict[str, MotorInfo],
                 min_turnaround: float,
                 min_interval: float,
                 completed_steps_lookup: List[int]):
        self.model = model
        self.output_triggers = output_triggers
        self.axis_mapping = axis_mapping
        self.min_turnaround = min_turnaround
        self.min_interval = min_interval
        self.completed_steps_lookup = completed_steps_lookup

        self.profile: PmacTrajectoryProfile = PmacTrajectoryProfile.empty()

    def calculate_profile_from_velocities(self,
                                          time_arrays: AxisProfileArrays,
                                          velocity_arrays: AxisProfileArrays,
                                          current_positions: Dict[str, float],
                                          completed_steps: int):
        # at this point we have time/velocity arrays with 2-4 values for each
        # axis. Each time represents a (instantaneous) change in acceleration.
        # We want to translate this into a move profile (time/position).
        # Every axis profile must have a point for each of the times from
        # all axes combined

        # extract the time points from all axes
        t_list = []
        for time_array in time_arrays.values():
            t_list.extend(time_array)
        combined_times = np.array(t_list)
        combined_times = np.unique(combined_times)
        # remove the 0 time initial point
        combined_times = list(np.sort(combined_times))[1:]
        num_intervals = len(combined_times)

        # set up the time, mode and user arrays for the control
        prev_time = 0
        time_intervals = []
        for t in combined_times:
            # times are absolute - convert to intervals
            time_intervals.append(t - prev_time)
            prev_time = t

        self.profile.time_array += time_intervals
        self.profile.velocity_mode += \
            [VelocityMode.PREV_TO_CURRENT] * num_intervals
        user_program = get_user_program(self.output_triggers,
                                        PointType.TURNAROUND)
        self.profile.user_programs += [user_program] * num_intervals
        self.completed_steps_lookup += [completed_steps] * num_intervals

        # Do this for each axis' velocity and time arrays
        for axis_name, motor_info in self.axis_mapping.items():
            axis_times = time_arrays[axis_name]
            axis_velocities = velocity_arrays[axis_name]
            prev_velocity = axis_velocities[0]
            position = current_positions[axis_name]
            # tracks the accumulated interpolated interval time since the
            # last axis velocity profile point
            time_interval = 0
            # At this point we have time/velocity arrays with multiple values
            # some of which align with the axis_times and some interleave.
            # We want to create a matching move profile of 'num_intervals'
            axis_pt = 1
            for i in range(num_intervals):
                axis_velocity = axis_velocities[axis_pt]
                axis_prev_velocity = axis_velocities[axis_pt - 1]
                axis_interval = axis_times[axis_pt] - axis_times[axis_pt - 1]

                if np.isclose(combined_times[i], axis_times[axis_pt]):
                    # this combined point matches the axis point
                    # use the axis velocity and move to the next axis point
                    this_velocity = axis_velocities[axis_pt]
                    axis_pt += 1
                    time_interval = 0
                else:
                    # this combined point is between two axis points,
                    # interpolate the velocity between those axis points
                    time_interval += time_intervals[i]
                    fraction = time_interval / axis_interval
                    dv = axis_velocity - axis_prev_velocity
                    this_velocity = axis_prev_velocity + fraction * dv

                part_position = motor_info.ramp_distance(
                    prev_velocity, this_velocity, time_intervals[i])
                prev_velocity = this_velocity

                position += part_position
                self.profile[motor_info.cs.axis.upper()].append(position)

    def add_profile_point(self, time_point, velocity_mode, user_program,
                          completed_step, axis_points):
        # Add padding if the move time exceeds the max pmac move time
        if time_point > MAX_MOVE_TIME:
            assert self.profile.time_array, \
                "Can't stretch the first point of a profile"
            nsplit = int(time_point / MAX_MOVE_TIME + 1)
            for _ in range(nsplit):
                self.profile.time_array.append(time_point / nsplit)
            for _ in range(nsplit - 1):
                self.profile.velocity_mode.append(VelocityMode.PREV_TO_NEXT)
                self.profile.user_programs.append(UserProgram.NO_PROGRAM)
            for k, v in axis_points.items():
                cs_axis = self.axis_mapping[k].cs.axis.upper()
                last_point = self.profile[cs_axis][-1]
                per_section = float(v - last_point) / nsplit
                for i in range(1, nsplit):
                    self.profile[cs_axis].append(
                        last_point + i * per_section)
            last_completed_step = self.completed_steps_lookup[-1]
            for _ in range(nsplit - 1):
                self.completed_steps_lookup.append(last_completed_step)
        else:
            # Add point
            self.profile.time_array.append(time_point)

        # Set the requested point
        self.profile.velocity_mode.append(velocity_mode)
        self.profile.user_programs.append(user_program)
        self.completed_steps_lookup.append(completed_step)
        for k, v in axis_points.items():
            cs_axis = self.axis_mapping[k].cs.axis.upper()
            self.profile[cs_axis].append(v)

    def add_generator_point_pair(self, point, point_num, points_are_joined):
        # Add position
        user_program = get_user_program(self.output_triggers,
                                        PointType.MID_POINT)
        self.add_profile_point(point.duration / 2.0,
                               VelocityMode.PREV_TO_NEXT, user_program,
                               point_num,
                               {name: point.positions[name] for name in
                                self.axis_mapping})

        # insert the lower bound of the next frame
        if points_are_joined:
            user_program = get_user_program(self.output_triggers,
                                            PointType.POINT_JOIN)
            velocity_point = VelocityMode.PREV_TO_NEXT
        else:
            user_program = get_user_program(self.output_triggers,
                                            PointType.END_OF_ROW)
            velocity_point = VelocityMode.PREV_TO_CURRENT

        self.add_profile_point(
            point.duration / 2.0, velocity_point, user_program, point_num + 1,
            {name: point.upper[name] for name in self.axis_mapping})

    def add_sparse_point(self, point, point_num, next_point, points_are_joined):
        # todo when branch velocity-mode-changes is merged we will
        #  need to set velocity mode CURRENT_TO_NEXT on the *previous*
        #  point whenever we skip a point
        if self.time_since_last_pvt > 0 and not points_are_joined:
            # assume we can skip if we are at the end of a row and we
            # just skipped the most recent point (i.e. time_since_last_pvt > 0)
            do_skip = True
        else:
            # otherwise skip this point if is is linear to previous point
            do_skip = next_point and points_are_joined and \
                      self.is_same_velocity(point, next_point)

        if do_skip:
            self.time_since_last_pvt += point.duration
        else:
            # not skipping - add this mid point
            user_program = get_user_program(self.output_triggers,
                                            PointType.MID_POINT)
            self.add_profile_point(
                self.time_since_last_pvt + point.duration / 2.0,
                VelocityMode.PREV_TO_NEXT, user_program, point_num,
                {name: point.positions[name] for name in self.axis_mapping})
            self.time_since_last_pvt = point.duration / 2.0

        # insert the lower bound of the next frame
        if points_are_joined:
            user_program = get_user_program(self.output_triggers,
                                            PointType.POINT_JOIN)
            velocity_point = VelocityMode.PREV_TO_NEXT
        else:
            user_program = get_user_program(self.output_triggers,
                                            PointType.END_OF_ROW)
            velocity_point = VelocityMode.PREV_TO_CURRENT

        # only add the lower bound if we did not skip this point OR if we are
        # at the end of a row where we always require a final point
        if not do_skip or not points_are_joined:
            self.add_profile_point(
                self.time_since_last_pvt, velocity_point,
                user_program, point_num + 1,
                {name: point.upper[name] for name in self.axis_mapping})
            self.time_since_last_pvt = 0

    def calculate_generator_profile(self, start_index: int,
                                    do_run_up: bool = False) -> PmacTrajectoryProfile:
        # If we are doing the first build, do_run_up will be passed to flag
        # that we need a run up, else just continue from the previous point
        if do_run_up:
            point = self.model.generator.get_point(start_index)

            # Calculate how long to leave for the run-up (at least MIN_TIME)
            run_up_time = MIN_TIME
            axis_points = {}
            for axis_name, velocity in point_velocities(
                    self.axis_mapping, point).items():
                axis_points[axis_name] = point.lower[axis_name]
                motor_info = self.axis_mapping[axis_name]
                run_up_time = max(run_up_time,
                                  motor_info.acceleration_time(0, velocity))

            # Add lower bound
            user_program = get_user_program(self.output_triggers,
                                            PointType.START_OF_ROW)
            self.add_profile_point(
                run_up_time, VelocityMode.PREV_TO_CURRENT, user_program,
                start_index, axis_points)

        self.time_since_last_pvt = 0
        for i in range(start_index, self.model.end_index):
            point = self.model.generator.get_point(i)

            if i + 1 < self.model.end_index:
                # Check if we need to insert the lower bound of next_point
                next_point = self.model.generator.get_point(i + 1)

                points_are_joined = points_joined(
                    self.axis_mapping, point, next_point
                )
            else:
                points_are_joined = False
                next_point = None

            if self.output_triggers == MotionTrigger.EVERY_POINT:
                self.add_generator_point_pair(point, i, points_are_joined)
            else:
                self.add_sparse_point(point, i, next_point, points_are_joined)

            # add in the turnaround between non-contiguous points
            # or after the last point if delay_after is defined
            if not points_are_joined:
                if next_point is not None:
                    self.insert_gap(point, next_point, i + 1)
                elif getattr(point, "delay_after", None) is not None:
                    pass

            # Check if we have exceeded the points number and need to write
            # Strictly less than so we always add one more point to the time
            # array so we can always stretch points in a subsequent add with
            # the values already in the profiles
            if len(self.profile.time_array) > PROFILE_POINTS:
                self.model.end_index = i + 1
                return

        self.add_tail_off()
        return self.profile

    def add_tail_off(self):
        # Add the last tail off point
        point = self.model.generator.get_point(self.model.end_index - 1)
        # Calculate how long to leave for the tail-off
        # #(at least MIN_TIME)
        axis_points = {}
        tail_off_time = MIN_TIME
        for axis_name, velocity in point_velocities(
                self.axis_mapping, point, entry=False).items():
            motor_info = self.axis_mapping[axis_name]
            tail_off_time = max(tail_off_time,
                                motor_info.acceleration_time(0,
                                                             velocity))
            tail_off = motor_info.ramp_distance(velocity, 0)
            axis_points[axis_name] = point.upper[axis_name] + tail_off
        # Do the last move
        user_program = get_user_program(self.output_triggers,
                                        PointType.TURNAROUND)
        self.add_profile_point(tail_off_time, VelocityMode.ZERO_VELOCITY,
                               user_program,
                               self.model.end_index, axis_points)
        self.end_index = self.model.end_index

    def insert_gap(self, point, next_point, completed_steps):
        # Work out the velocity profiles of how to move to the start
        min_turnaround = max(self.min_turnaround,
                             getattr(point, "delay_after", None))
        time_arrays, velocity_arrays = profile_between_points(
            self.axis_mapping, point, next_point, min_turnaround,
            self.min_interval)

        start_positions = {}
        for axis_name in self.axis_mapping:
            start_positions[axis_name] = point.upper[axis_name]

        # Work out the Position trajectories from these profiles
        self.calculate_profile_from_velocities(
            time_arrays, velocity_arrays, start_positions, completed_steps)

        # make sure the last point is the same as next_point.lower since
        # calculate_profile_from_velocities fails when the turnaround is 2
        # points only
        for axis_name, motor_info in self.axis_mapping.items():
            self.profile[motor_info.cs.axis.upper()][-1] = \
                next_point.lower[axis_name]

        # Change the last point to be a live frame
        self.profile.velocity_mode[-1] = VelocityMode.PREV_TO_CURRENT
        user_program = get_user_program(self.output_triggers,
                                        PointType.START_OF_ROW)
        self.profile.user_programs[-1] = user_program

    def is_same_velocity(self, p1, p2):
        result = False
        if p2.duration == p2.duration:
            result = True
            for axis_name, _ in self.axis_mapping.items():
                if not np.isclose(
                        p1.lower[axis_name] - p1.positions[axis_name],
                        p2.lower[axis_name] - p2.positions[axis_name]
                ) or not np.isclose(
                    p1.positions[axis_name] - p1.upper[axis_name],
                    p2.positions[axis_name] - p2.upper[axis_name]
                ):
                    result = False
                    break
        return result
