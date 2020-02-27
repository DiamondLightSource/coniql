from typing import Dict, Optional

import numpy as np

# Number of seconds that a control tick is
from scanpointgenerator import CompoundGenerator, Point

from device.devices.pmac import Pmac
from device.pmac.profileio import write_profile
from device.pmac.util import point_velocities
from device.pmac.motorinfo import MotorInfo
from device.pmac.control.motionaxes import cs_port_with_motors_in, \
    get_motion_axes, cs_axis_mapping
from device.pmac.profile.trajectoryprofile import PmacTrajectoryProfile, ProfileGenerator
from device.pmac.modes import MIN_TIME, MIN_INTERVAL, UserProgram
from device.pmac.control.trajectorymodel import TrajectoryModel
from device.scan.util import MotionTrigger
from device.scan.movetopoint import move_to_point


async def scan_points(pmac: Pmac, model: TrajectoryModel):
    """The selected pmac will scan through the points provided by the
    control model. Assuming the axis labels match scannables attached
    said pmac and all the axes are in the same coordinate system"""
    revised_generator = await validate_trajectory_scan(pmac, model)
    if revised_generator is not None:
        revised_generator.prepare()
        model = model.with_revised_generator(revised_generator)
    await configure_pmac_for_scan(pmac, model)
    await pmac.trajectory.execute_profile()


async def configure_pmac_for_scan(pmac: Pmac,
                                  model: TrajectoryModel):
    # Store what sort of triggers we need to output
    # output_triggers = get_motion_trigger(part_info)
    output_triggers = MotionTrigger.EVERY_POINT

    # Check if we should be taking part in the scan
    motion_axes = get_motion_axes(model.generator)
    need_gpio = output_triggers != MotionTrigger.NONE
    if not (motion_axes or need_gpio):
        # This pmac has nothing to do for this scan
        return

    min_turnaround = MIN_TIME
    min_interval = MIN_INTERVAL

    # Work out the cs_port we should be using
    # layout_table = self.pmac.control.axis_motors
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
    await move_to_start(pmac, model, axis_mapping)

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
            model,
            output_triggers,
            axis_mapping,
            min_turnaround,
            min_interval,
            completed_steps_lookup
        )
    profile = profile_generator.calculate_generator_profile(
        model.start_index, do_run_up=True)
    await write_profile_points(pmac, profile, cs_port)


async def write_profile_points(pmac: Pmac, profile: PmacTrajectoryProfile,
                         cs_port: Optional[str] = None):
    """Build profile using given data
    """
    await write_profile(pmac, profile.with_ticks(), cs_port)


async def move_to_start(pmac: Pmac,
                        model: TrajectoryModel,
                        axis_mapping: Dict[str, MotorInfo]):
    first_pt = first_point(model)
    starting_pos = starting_position(first_pt, axis_mapping)
    await move_to_point(pmac.motors.iterator(), starting_pos)


def starting_position(first_point: Point,
                      axis_mapping: Dict[str, MotorInfo]) -> Point:
    starting_pos = Point()
    for axis_name, velocity in point_velocities(
            axis_mapping, first_point).items():
        motor_info = axis_mapping[axis_name]
        acceleration_distance = motor_info.ramp_distance(0, velocity)
        runup_position = first_point.lower[axis_name] - acceleration_distance
        starting_pos.positions[axis_name] = runup_position
    return starting_pos


def first_point(model: TrajectoryModel) -> Point:
    return model.generator.get_point(model.start_index)


async def validate_trajectory_scan(pmac: Pmac, model: TrajectoryModel) -> \
        Optional[CompoundGenerator]:
    # If GPIO not demanded for every point we don't need to align to the
    # servo cycle
    # trigger = get_motion_trigger(part_info)
    # if trigger != MotionTrigger.EVERY_POINT:
    #     return
    # TODO: Reinstate this when we have some equalivalent of part info

    # Find the duration
    point_duration = model.generator.duration
    assert point_duration > 0, \
        "Can only do fixed duration at the moment"
    servo_freq = await pmac.servo_frequency()
    # convert half an exposure to multiple of servo ticks, rounding down
    ticks = np.floor(servo_freq * 0.5 * point_duration)
    if not np.isclose(servo_freq, 3200):
        # + 0.002 for some observed jitter in the servo frequency if I10
        # isn't a whole number of 1/4 us move timer ticks
        # (any frequency apart from 3.2 kHz)
        ticks += 0.002
    # convert to integer number of microseconds, rounding up
    micros = np.ceil(ticks / servo_freq * 1e6)
    # back to duration
    duration = 2 * float(micros) / 1e6
    if duration != point_duration:
        serialized = model.generator.to_dict()
        new_generator = CompoundGenerator.from_dict(serialized)
        new_generator.duration = duration
        return new_generator


    # TODO: Figure out what this is and how it fits in
    # async def update_step(model: TrajectoryModel, scanned: int):
    #     # scanned is an index into the completed_steps_lookup, so a
    #     # "how far through the pmac control" rather than a generator
    #     # scan step
    #     if scanned > 0:
    #         completed_steps = self.completed_steps_lookup[scanned - 1]
    #         # Keep PROFILE_POINTS control points in front
    #         if not self.loading and self.end_index < self.steps_up_to and \
    #                 len(self.completed_steps_lookup) - scanned < PROFILE_POINTS:
    #             self.loading = True
    #             profile = self.calculate_generator_profile(self.end_index)
    #             await self.write_profile_points(profile)
    #             self.loading = False
    #
    #         # If we got to the end, there might be some leftover points that
    #         # need to be appended to finish
    #         if not self.loading and self.end_index == self.steps_up_to and \
    #                 self.profile.time_array:
    #             self.loading = True
    #             self.calculate_generator_profile(self.end_index)
    #             await self.write_profile_points()
    #             assert not self.profile.time_array, \
    #                 "Why do we still have points? %s" % self.profile
    #             self.loading = False
    #
