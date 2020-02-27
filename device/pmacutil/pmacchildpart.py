import asyncio
from typing import Any, List, Dict, Optional

import numpy as np

# Number of seconds that a trajectory tick is
from scanpointgenerator import CompoundGenerator, Point

from device.devices.pmac import Pmac
from device.pmacutil.profileio import write_profile
from device.pmacutil.pmacutil import cs_axis_mapping, \
    cs_port_with_motors_in, get_motion_axes, get_motion_trigger, \
    point_velocities, MotorInfo
from device.pmacutil.profile import PmacTrajectoryProfile, ProfileGenerator, \
    PROFILE_POINTS
from device.pmacutil.pmacconst import MIN_TIME, MIN_INTERVAL, UserProgram
from device.scanutil.scanningutil import MotionTrigger, \
    ParameterTweakInfo, RunProgressInfo
from device.scanutil.movetopoint import move_to_point


async def configure_pmac_for_scan(pmac: Pmac,
                            generator: CompoundGenerator,
                            completed_steps: int = 0,
                            steps_to_do: Optional[int] = None):
    steps_to_do = steps_to_do or len(list(generator.iterator()))

    # Store what sort of triggers we need to output
    # output_triggers = get_motion_trigger(part_info)
    output_triggers = MotionTrigger.EVERY_POINT

    # Check if we should be taking part in the scan
    motion_axes = get_motion_axes(generator)
    need_gpio = output_triggers != MotionTrigger.NONE
    if not (motion_axes or need_gpio):
        # This pmac has nothing to do for this scan
        return

    min_turnaround = MIN_TIME
    min_interval = MIN_INTERVAL

    # Work out the cs_port we should be using
    # layout_table = self.pmac.trajectory.axis_motors
    if motion_axes:
        axis_mapping = await cs_axis_mapping(pmac.motors, motion_axes)
        # Check units for everything in the axis mapping
        # TODO: reinstate this when GDA does it properly
        # for axis_name, motor_info in sorted(self.axis_mapping.items()):
        #     assert motor_info.units == generator.units[axis_name], \
        #         "%s: Expected scan units of %r, got %r" % (
        #         axis_name, motor_info.units, generator.units[axis_name])
        # Guaranteed to have an entry in axis_mapping otherwise
        # cs_axis_mapping would fail, so pick its cs_port
        cs_port = list(axis_mapping.values())[0].cs.port
    else:
        # No axes to move, but if told to output triggers we still need to
        # do something
        axis_mapping = {}
        # Pick the first cs we find that has an axis assigned
        cs_port = await cs_port_with_motors_in(pmac.motors)

    clean_profile = PmacTrajectoryProfile(
        time_array=[MIN_TIME],
        user_programs=[UserProgram.ZERO_PROGRAM.real]
    )
    await write_profile(pmac, clean_profile, cs_port)
    await pmac.trajectory.execute_profile()
    await move_to_start(pmac, generator, axis_mapping, completed_steps)

    steps_up_to = completed_steps + steps_to_do
    completed_steps_lookup = []
    # Reset the profiles that still need to be sent
    # self.profile = dict(
    #     timeArray=[],
    #     velocityMode=[],
    #     userPrograms=[],
    # )
    time_since_last_pvt = 0
    # for info in self.axis_mapping.values():
    #     self.profile[info.cs_axis.lower()] = []
    profile_generator = ProfileGenerator(
            generator,
            output_triggers,
            axis_mapping,
            steps_up_to,
            min_turnaround,
            min_interval,
            completed_steps_lookup
        )
    profile = profile_generator.calculate_generator_profile(
        completed_steps, do_run_up=True)
    await write_profile_points(pmac, profile, cs_port)


async def write_profile_points(pmac: Pmac, profile: PmacTrajectoryProfile,
                         cs_port: Optional[str] = None):
    """Build profile using given data
    """
    await write_profile(pmac, profile.with_ticks(), cs_port)


async def move_to_start(pmac: Pmac, generator: CompoundGenerator,
                        axis_mapping: Dict[str, MotorInfo],
                        completed_steps: int):
    first_point = generator.get_point(completed_steps)
    starting_pos = Point()
    for axis_name, velocity in point_velocities(
            axis_mapping, first_point).items():
        motor_info = axis_mapping[axis_name]
        acceleration_distance = motor_info.ramp_distance(0, velocity)
        starting_pos.positions[axis_name] = first_point.lower[
                                                axis_name] - acceleration_distance
    await move_to_point(pmac.motors.iterator(), starting_pos)


class PmacChildPart:
    def __init__(self, pmac: Pmac):
        # type: (...) -> None
        # super(PmacChildPart, self).__init__(name, mri, initial_visibility)
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
        # self.profile = PmacTrajectoryProfile.empty()
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
        await self.move_to_point(starting_pos)


    async def move_to_point(self, point: Point):
        jobs = []
        for motor in self.pmac.motors.iterator():
            name = await motor.scannable_name.get()
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
        # layout_table = self.pmac.trajectory.axis_motors
        if motion_axes:
            self.axis_mapping = await cs_axis_mapping(self.pmac.motors, axesToMove)
            # Check units for everything in the axis mapping
            # TODO: reinstate this when GDA does it properly
            # for axis_name, motor_info in sorted(self.axis_mapping.items()):
            #     assert motor_info.units == generator.units[axis_name], \
            #         "%s: Expected scan units of %r, got %r" % (
            #         axis_name, motor_info.units, generator.units[axis_name])
            # Guaranteed to have an entry in axis_mapping otherwise
            # cs_axis_mapping would fail, so pick its cs_port
            cs_port = list(self.axis_mapping.values())[0].cs.port
        else:
            # No axes to move, but if told to output triggers we still need to
            # do something
            self.axis_mapping = {}
            # Pick the first cs we find that has an axis assigned
            cs_port = await cs_port_with_motors_in(self.pmac.motors)

        # Reset GPIOs
        # TODO: we might need to put this in pause if the PandA logic doesn't
        # copy with a trigger staying high
        clean_profile = PmacTrajectoryProfile(
            time_array=[MIN_TIME],
            user_programs=[UserProgram.ZERO_PROGRAM.real]
        )
        await write_profile(self.pmac, clean_profile, cs_port)
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
        profile = self.calculate_generator_profile(completed_steps, do_run_up=True)
        await self.write_profile_points(profile, cs_port)
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

    async def update_step(self, scanned):
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
                profile = self.calculate_generator_profile(self.end_index)
                await self.write_profile_points(profile)
                self.loading = False

            # If we got to the end, there might be some leftover points that
            # need to be appended to finish
            # if not self.loading and self.end_index == self.steps_up_to and \
            #         self.profile.time_array:
            #     self.loading = True
            #     self.calculate_generator_profile(self.end_index)
            #     await self.write_profile_points()
            #     assert not self.profile.time_array, \
            #         "Why do we still have points? %s" % self.profile
            #     self.loading = False

    async def write_profile_points(self, profile: PmacTrajectoryProfile,
                                   cs_port: str = None):
        """Build profile using given data
        """
        await write_profile(self.pmac, profile.with_ticks(), cs_port)

    def calculate_generator_profile(self, start_index: int,
                                    do_run_up: bool = False) -> PmacTrajectoryProfile:
        return self.make_profile_generator().calculate_generator_profile(
            start_index, do_run_up)

    def make_profile_generator(self) -> ProfileGenerator:
        return ProfileGenerator(
            self.generator,
            self.output_triggers,
            self.axis_mapping,
            self.steps_up_to,
            self.min_turnaround,
            self.min_interval,
            self.completed_steps_lookup
        )
