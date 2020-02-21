import asyncio
import re
from typing import Any, List

import numpy as np
from enum import IntEnum

# Number of seconds that a trajectory tick is
from scanpointgenerator import CompoundGenerator, Point

from device.devices.pmac import Pmac, PmacTrajectory
from device.pmacutil.pmactrajectorypart import PmacTrajectoryPart
from device.pmacutil.pmacutil import cs_axis_mapping, \
    cs_port_with_motors_in, get_motion_axes, get_motion_trigger, \
    point_velocities, points_joined, profile_between_points, \
    PmacTrajectoryProfile
from device.pmacutil.pmacconst import MIN_TIME, MIN_INTERVAL, CS_AXIS_NAMES
from device.pmacutil.scanningutil import MinTurnaroundInfo, MotionTrigger, \
    ParameterTweakInfo, RunProgressInfo

TICK_S = 0.000001

# Longest move time we can request
MAX_MOVE_TIME = 4.0


# velocity modes
class VelocityModes:
    PREV_TO_NEXT = 0
    PREV_TO_CURRENT = 1
    CURRENT_TO_NEXT = 2
    ZERO_VELOCITY = 3


# user programs
class UserPrograms:
    NO_PROGRAM = 0  # Do nothing
    LIVE_PROGRAM = 1  # GPIO123 = 1, 0, 0
    DEAD_PROGRAM = 2  # GPIO123 = 0, 1, 0
    MID_PROGRAM = 4  # GPIO123 = 0, 0, 1
    ZERO_PROGRAM = 8  # GPIO123 = 0, 0, 0


class PointType(IntEnum):
    START_OF_ROW = 0  # Lower bound of first point of row
    MID_POINT = 1  # Position of any point
    POINT_JOIN = 2  # Boundary of two joined points
    END_OF_ROW = 3  # Upper boundary of last point of row
    TURNAROUND = 4  # Between rows


# How many profile points to write each time
PROFILE_POINTS = 10000


class PmacChildPart:
    def __init__(self, traj: PmacTrajectoryPart, pmac: Pmac):
        # type: (...) -> None
        # super(PmacChildPart, self).__init__(name, mri, initial_visibility)
        self.traj = traj
        self.pmac = pmac
        # Axis information stored from validate
        self.axis_mapping = None  # type: Dict[str, MotorInfo]
        # Lookup of the completed_step value for each point
        self.completed_steps_lookup = []  # type: List[int]
        # The minimum turnaround time for non-joined points
        self.min_turnaround = 0
        # The minimum turnaround time for non-joined points
        self.min_interval = 0
        # If we are currently loading then block loading more points
        self.loading = False
        # Where we have generated into profile
        self.end_index = 0
        # Where we should stop loading points
        self.steps_up_to = 0
        # What sort of triggers to output
        self.output_triggers = None
        # Profile points that haven't been sent yet
        # {timeArray/velocityMode/userPrograms/a/b/c/u/v/w/x/y/z: [elements]}
        self.profile = PmacTrajectoryProfile.empty()
        # accumulated intervals since the last PVT point used by sparse
        # trajectory logic
        self.time_since_last_pvt = 0
        # Stored generator for positions
        self.generator = None  # type: CompoundGenerator

    # def notify_dispatch_request(self, request):
    #     # type: (Request) -> None
    #     if isinstance(request, Put) and request.path[1] == "design":
    #         # We have hooked self.reload to PreConfigure, and reload() will
    #         # set design attribute, so explicitly allow this without checking
    #         # it is in no_save (as it won't be in there)
    #         pass
    #     else:
    #         super(PmacChildPart, self).notify_dispatch_request(request)

    # def on_reset(self, context):
    #     # type: (builtin.hooks.AContext) -> None
    #     super(PmacChildPart, self).on_reset(context)
    #     self.on_abort(context)

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    def on_validate(self,
                    context,  # type: scanning.hooks.AContext
                    generator,  # type: scanning.hooks.AGenerator
                    axesToMove,  # type: scanning.hooks.AAxesToMove
                    part_info,  # type: scanning.hooks.APartInfo
                    ):
        # type: (...) -> scanning.hooks.UParameterTweakInfos
        # child = context.block_view(self.mri)
        # Check that we can move all the requested axes
        available = set(map(lambda t: t[0],
                            self.pmac.trajectory.axis_motors.available_axes()))
        motion_axes = get_motion_axes(generator, axesToMove)
        assert available.issuperset(motion_axes), \
            "Some of the requested axes %s are not on the motor list %s" % (
                list(axesToMove), sorted(available))
        # If GPIO not demanded for every point we don't need to align to the
        # servo cycle
        trigger = get_motion_trigger(part_info)
        if trigger != MotionTrigger.EVERY_POINT:
            return
        # Find the duration
        assert generator.duration > 0, \
            "Can only do fixed duration at the moment"
        servo_freq = self.pmac.servoFrequency()
        # convert half an exposure to multiple of servo ticks, rounding down
        ticks = np.floor(servo_freq * 0.5 * generator.duration)
        if not np.isclose(servo_freq, 3200):
            # + 0.002 for some observed jitter in the servo frequency if I10
            # isn't a whole number of 1/4 us move timer ticks
            # (any frequency apart from 3.2 kHz)
            ticks += 0.002
        # convert to integer number of microseconds, rounding up
        micros = np.ceil(ticks / servo_freq * 1e6)
        # back to duration
        duration = 2 * float(micros) / 1e6
        if duration != generator.duration:
            serialized = generator.to_dict()
            new_generator = CompoundGenerator.from_dict(serialized)
            new_generator.duration = duration
            return ParameterTweakInfo("generator", new_generator)

    # def move_to_start_old(self, cs_port, completed_steps):
    #     # type: (Block, str, int) -> Future
    #     # Work out what method to call
    #     match = re.search(r"\d+$", cs_port)
    #     assert match, "Cannot extract CS number from CS port '%s'" % cs_port
    #     move_async = child["moveCS%s_async" % match.group()]
    #     # Set all the axes to move to the start positions
    #     first_point = self.generator.get_point(completed_steps)
    #     args = {}
    #     move_to_start_time = 0.0
    #     for axis_name, velocity in point_velocities(
    #             self.axis_mapping, first_point).items():
    #         motor_info = self.axis_mapping[axis_name]  # type: MotorInfo
    #         acceleration_distance = motor_info.ramp_distance(0, velocity)
    #         start_pos = first_point.lower[axis_name] - acceleration_distance
    #         args[motor_info.cs_axis.lower()] = start_pos
    #         # Time profile that the move is likely to take
    #         # NOTE: this is only accurate if pmac max velocity in linear motion
    #         # prog is set to same speed as motor record VMAX
    #         profile = motor_info.make_velocity_profile(
    #             0, 0, motor_info.current_position - start_pos, 0)
    #         times, _ = profile.make_arrays()
    #         move_to_start_time = max(times[-1], move_to_start_time)
    #     # Call the method with the values
    #     fs = move_async(moveTime=move_to_start_time, **args)
    #     return fs

    async def move_to_start(self, completed_steps: int):
        first_point = self.generator.get_point(completed_steps)
        starting_pos = Point()
        for axis_name, velocity in point_velocities(
                self.axis_mapping, first_point).items():
            motor_info = self.axis_mapping[axis_name]
            acceleration_distance = motor_info.ramp_distance(0, velocity)
            starting_pos.positions[axis_name] = first_point.lower[
                                                    axis_name] - acceleration_distance

    async def move_to_point(self, point: Point):
        jobs = []
        for name, motor in self.pmac.trajectory.axis_motors.available_axes():
            if name in point.positions:
                pos = point.positions[name]
                jobs.append(motor.setpoint.put(pos))
        return await asyncio.wait(jobs)

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    async def on_configure(self,
                           completed_steps: int,
                           steps_to_do: int,
                           part_info: Any,
                           generator: CompoundGenerator,
                           axesToMove: List[str],
                           # type: scanning.hooks.AAxesToMove
                           ):
        # context.unsubscribe_all()
        # child = context.block_view(self.mri)

        # Store what sort of triggers we need to output
        self.output_triggers = get_motion_trigger(part_info)

        # Check if we should be taking part in the scan
        motion_axes = get_motion_axes(generator, axesToMove)
        need_gpio = self.output_triggers != MotionTrigger.NONE
        if motion_axes or need_gpio:
            # Taking part, so store generator
            self.generator = generator
        else:
            # Flag as not taking part
            self.generator = None
            return

        # See if there is a minimum turnaround
        # infos = MinTurnaroundInfo.filter_values(part_info)
        # if infos:
        #     assert len(infos) == 1, \
        #         "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(infos)
        #     self.min_turnaround = max(MIN_TIME, infos[0].gap)
        #     self.min_interval = infos[0].interval
        # else:
        self.min_turnaround = MIN_TIME
        self.min_interval = MIN_INTERVAL

        # Work out the cs_port we should be using
        layout_table = self.pmac.trajectory.axis_motors
        if motion_axes:
            self.axis_mapping = await cs_axis_mapping(layout_table, motion_axes)
            # Check units for everything in the axis mapping
            # TODO: reinstate this when GDA does it properly
            # for axis_name, motor_info in sorted(self.axis_mapping.items()):
            #     assert motor_info.units == generator.units[axis_name], \
            #         "%s: Expected scan units of %r, got %r" % (
            #         axis_name, motor_info.units, generator.units[axis_name])
            # Guaranteed to have an entry in axis_mapping otherwise
            # cs_axis_mapping would fail, so pick its cs_port
            cs_port = list(self.axis_mapping.values())[0].cs_port
        else:
            # No axes to move, but if told to output triggers we still need to
            # do something
            self.axis_mapping = {}
            # Pick the first cs we find that has an axis assigned
            cs_port = await cs_port_with_motors_in(layout_table)

        # Reset GPIOs
        # TODO: we might need to put this in pause if the PandA logic doesn't
        # copy with a trigger staying high
        clean_profile = PmacTrajectoryProfile(
            time_array=[MIN_TIME],
            user_programs=[UserPrograms.ZERO_PROGRAM.real]
        )
        await self.traj.write_profile(clean_profile, cs_port)
        await self.pmac.trajectory.execute_profile()
        await self.move_to_start(completed_steps)
        # if motion_axes:
        #     # Start off the move to the start
        #     fs = self.move_to_start(completed_steps)
        # else:
        #     fs = []
        # Set how far we should be going and the completed steps lookup
        self.steps_up_to = completed_steps + steps_to_do
        self.completed_steps_lookup = []
        # Reset the profiles that still need to be sent
        # self.profile = dict(
        #     timeArray=[],
        #     velocityMode=[],
        #     userPrograms=[],
        # )
        self.time_since_last_pvt = 0
        # for info in self.axis_mapping.values():
        #     self.profile[info.cs_axis.lower()] = []
        self.calculate_generator_profile(completed_steps, do_run_up=True)
        await self.write_profile_points(cs_port)
        # Wait for the motors to have got to the start
        # context.wait_all_futures(fs)

    async def on_run(self):
        # type: (scanning.hooks.AContext) -> None
        if self.generator:
            self.loading = False
            # child = context.block_view(self.mri)
            # Wait for the trajectory to run and complete

            # TODO: Update step Callum
            # child.pointsScanned.subscribe_value(self.update_step, child)

            # TODO: we should return at the end of the last point for PostRun
            # child.executeProfile()
            await self.pmac.trajectory.execute_profile()

    async def on_abort(self):
        if self.generator:
            # child = context.block_view(self.mri)
            # TODO: if we abort during move to start, what happens?
            # child.abortProfile()
            await self.pmac.trajectory.abort()

    def update_step(self, scanned):
        # scanned is an index into the completed_steps_lookup, so a
        # "how far through the pmac trajectory" rather than a generator
        # scan step
        if scanned > 0:
            completed_steps = self.completed_steps_lookup[scanned - 1]
            self.registrar.report(RunProgressInfo(
                completed_steps))
            # Keep PROFILE_POINTS trajectory points in front
            if not self.loading and self.end_index < self.steps_up_to and \
                    len(self.completed_steps_lookup) - scanned < PROFILE_POINTS:
                self.loading = True
                self.calculate_generator_profile(self.end_index)
                self.write_profile_points()
                self.loading = False

            # If we got to the end, there might be some leftover points that
            # need to be appended to finish
            if not self.loading and self.end_index == self.steps_up_to and \
                    self.profile.time_array:
                self.loading = True
                self.calculate_generator_profile(self.end_index)
                self.write_profile_points()
                assert not self.profile.time_array, \
                    "Why do we still have points? %s" % self.profile
                self.loading = False

    async def write_profile_points(self, cs_port=None):
        """Build profile using given data
        Args:
            child (Block): Child block for running
            cs_port (str): CS Port if this is a build rather than append
        """
        # These are the things we will send
        args = {}
        if cs_port is not None:
            args["cs_port"] = cs_port

        # Time array
        overflow = 0.0
        time_array_ticks = []
        for t in self.profile.time_array:
            ticks = t / TICK_S
            overflow += (ticks % 1)
            ticks = int(ticks)
            if overflow > 0.5:
                overflow -= 1
                ticks += 1
            time_array_ticks.append(ticks)
        # TODO: overflow discarded overy 10000 points, is it a problem?
        self.profile.time_array = time_array_ticks  # np.array(time_array_ticks, np.int32)

        # Velocity Mode
        # self.profile.velocity_mode = np.array(
        #     self.profile.velocity_mode, np.int32)
        # self.profile.user_programs = np.array(
        #     self.profile.user_programs, np.int32)

        # for k, v in self.profile.items():
        #     # store the remnant back in the array
        #     self.profile[k] = v[PROFILE_POINTS:]
        #     v = v[:PROFILE_POINTS]
        #     if k == "time_array":
        #         overflow = 0.0
        #         time_array_ticks = []
        #         for t in v:
        #             ticks = t / TICK_S
        #             overflow += (ticks % 1)
        #             ticks = int(ticks)
        #             if overflow > 0.5:
        #                 overflow -= 1
        #                 ticks += 1
        #             time_array_ticks.append(ticks)
        #         # TODO: overflow discarded overy 10000 points, is it a problem?
        #         v = np.array(time_array_ticks, np.int32)
        #     elif k in ("velocity_mode", "user_programs"):
        #         v = np.array(v, np.int32)
        #     else:
        #         v = np.array(v, np.float64)
        #     args[k] = v

        positions = {
            n.lower(): self.profile.axes[n] for n in CS_AXIS_NAMES
        }

        await self.traj.write_profile(
            self.profile,
            cs_port
        )

    def get_user_program(self, point_type):
        # type: (PointType) -> int
        if self.output_triggers == MotionTrigger.NONE:
            # Always produce no program
            return UserPrograms.NO_PROGRAM
        elif self.output_triggers == MotionTrigger.ROW_GATE:
            if point_type == PointType.START_OF_ROW:
                # Produce a gate for the whole row
                return UserPrograms.LIVE_PROGRAM
            elif point_type == PointType.END_OF_ROW:
                # Falling edge of row gate
                return UserPrograms.ZERO_PROGRAM
            else:
                # Otherwise don't change anything
                return UserPrograms.NO_PROGRAM
        else:
            if point_type in (PointType.START_OF_ROW, PointType.POINT_JOIN):
                return UserPrograms.LIVE_PROGRAM
            elif point_type == PointType.END_OF_ROW:
                return UserPrograms.DEAD_PROGRAM
            elif point_type == PointType.MID_POINT:
                return UserPrograms.MID_PROGRAM
            else:
                return UserPrograms.ZERO_PROGRAM

    def calculate_profile_from_velocities(self, time_arrays, velocity_arrays,
                                          current_positions, completed_steps):
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

        # set up the time, mode and user arrays for the trajectory
        prev_time = 0
        time_intervals = []
        for t in combined_times:
            # times are absolute - convert to intervals
            time_intervals.append(t - prev_time)
            prev_time = t

        self.profile.time_array += time_intervals
        self.profile.velocity_mode += \
            [VelocityModes.PREV_TO_CURRENT] * num_intervals
        user_program = self.get_user_program(PointType.TURNAROUND)
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
                self.profile[motor_info.cs_axis.lower()].append(position)

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
                self.profile.velocity_mode.append(VelocityModes.PREV_TO_NEXT)
                self.profile.user_programs.append(UserPrograms.NO_PROGRAM)
            for k, v in axis_points.items():
                cs_axis = self.axis_mapping[k].cs_axis.lower()
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
            cs_axis = self.axis_mapping[k].cs_axis.lower()
            self.profile[cs_axis].append(v)

    def add_generator_point_pair(self, point, point_num, points_are_joined):
        # Add position
        user_program = self.get_user_program(PointType.MID_POINT)
        self.add_profile_point(point.duration / 2.0,
                               VelocityModes.PREV_TO_NEXT, user_program,
                               point_num,
                               {name: point.positions[name] for name in
                                self.axis_mapping})

        # insert the lower bound of the next frame
        if points_are_joined:
            user_program = self.get_user_program(PointType.POINT_JOIN)
            velocity_point = VelocityModes.PREV_TO_NEXT
        else:
            user_program = self.get_user_program(PointType.END_OF_ROW)
            velocity_point = VelocityModes.PREV_TO_CURRENT

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
            user_program = self.get_user_program(PointType.MID_POINT)
            self.add_profile_point(
                self.time_since_last_pvt + point.duration / 2.0,
                VelocityModes.PREV_TO_NEXT, user_program, point_num,
                {name: point.positions[name] for name in self.axis_mapping})
            self.time_since_last_pvt = point.duration / 2.0

        # insert the lower bound of the next frame
        if points_are_joined:
            user_program = self.get_user_program(PointType.POINT_JOIN)
            velocity_point = VelocityModes.PREV_TO_NEXT
        else:
            user_program = self.get_user_program(PointType.END_OF_ROW)
            velocity_point = VelocityModes.PREV_TO_CURRENT

        # only add the lower bound if we did not skip this point OR if we are
        # at the end of a row where we always require a final point
        if not do_skip or not points_are_joined:
            self.add_profile_point(
                self.time_since_last_pvt, velocity_point,
                user_program, point_num + 1,
                {name: point.upper[name] for name in self.axis_mapping})
            self.time_since_last_pvt = 0

    def calculate_generator_profile(self, start_index, do_run_up=False):
        # If we are doing the first build, do_run_up will be passed to flag
        # that we need a run up, else just continue from the previous point
        if do_run_up:
            point = self.generator.get_point(start_index)

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
            user_program = self.get_user_program(PointType.START_OF_ROW)
            self.add_profile_point(
                run_up_time, VelocityModes.PREV_TO_CURRENT, user_program,
                start_index, axis_points)

        self.time_since_last_pvt = 0
        for i in range(start_index, self.steps_up_to):
            point = self.generator.get_point(i)

            if i + 1 < self.steps_up_to:
                # Check if we need to insert the lower bound of next_point
                next_point = self.generator.get_point(i + 1)

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
                self.end_index = i + 1
                return

        self.add_tail_off()

    def add_tail_off(self):
        # Add the last tail off point
        point = self.generator.get_point(self.steps_up_to - 1)
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
        user_program = self.get_user_program(PointType.TURNAROUND)
        self.add_profile_point(tail_off_time, VelocityModes.ZERO_VELOCITY,
                               user_program,
                               self.steps_up_to, axis_points)
        self.end_index = self.steps_up_to

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
            self.profile[motor_info.cs_axis.lower()][-1] = \
                next_point.lower[axis_name]

        # Change the last point to be a live frame
        self.profile.velocity_mode[-1] = VelocityModes.PREV_TO_CURRENT
        user_program = self.get_user_program(PointType.START_OF_ROW)
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
