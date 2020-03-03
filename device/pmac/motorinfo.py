from dataclasses import dataclass

from device.channel.multi import get_all
from device.pmac.deviceutil.motor import MotorCs
from device.pmac.protocol.motor import PmacMotor
from device.pmac.modes import CS_AXIS_NAMES
from device.pmac.profile.velocityprofile import VelocityProfile


@dataclass
class MotorInfo:
    cs: MotorCs
    acceleration: float
    resolution: float
    offset: float
    max_velocity: float
    current_position: float
    scannable: str
    velocity_settle: float
    units: str

    def acceleration_time(self, v1, v2):
        # The time taken to ramp from v1 to pad_velocity
        ramp_time = abs(v2 - v1) / self.acceleration
        return ramp_time

    def ramp_distance(self, v1, v2, ramp_time=None):
        # The distance moved in the first part of the ramp
        if ramp_time is None:
            ramp_time = self.acceleration_time(v1, v2)
        ramp_distance = (v1 + v2) * ramp_time / 2
        return ramp_distance

    def make_velocity_profile(
            self, v1, v2, distance, min_time, min_interval=0.002):
        """Calculate PVT points that will perform the move within motor params
        Args:
            v1 (float): Starting velocity in EGUs/s
            v2 (float): Ending velocity in EGUs/s
            distance (float): Relative distance to travel in EGUs
            min_time (float): The minimum time the move should take
            min_interval (float): Minimum time between profile points
        Returns:
            VelocityProfile: defining a list of times and velocities
        """

        # Create the time and velocity arrays
        p = VelocityProfile(
            v1, v2, distance, min_time, self.acceleration, self.max_velocity,
            self.velocity_settle, min_interval)
        p.get_profile()
        return p

    def in_cts(self, position):
        # type: (float) -> int
        """Return the position (in EGUs) translated to counts"""
        cts = int(round((position - self.offset) / self.resolution))
        return cts


async def motor_info(cs: MotorCs, name: str, motor: PmacMotor) -> MotorInfo:
    assert cs.axis in CS_AXIS_NAMES, \
        "Can only scan 1-1 mappings, %r is %r" % (
            name, cs.axis)

    max_velocity, acceleration_time, resolution, offset, current_position, units = await get_all(
        motor.max_velocity,
        motor.acceleration_time,
        motor.resolution,
        motor.offset,
        motor.position,
        motor.units)

    acceleration = float(max_velocity) / acceleration_time
    return MotorInfo(
        cs=cs,
        acceleration=acceleration,
        resolution=resolution,
        offset=offset,
        max_velocity=max_velocity,
        current_position=current_position,
        scannable=name,
        velocity_settle=0.0,
        units=units
    )