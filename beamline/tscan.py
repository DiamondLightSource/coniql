import asyncio
from typing import Dict

from scanpointgenerator import LineGenerator, CompoundGenerator, Point

from beamline.scanenv import make_env, AdSimScanEnvironment
from device.devices.positioner import PositionerWithStatus

xs = LineGenerator("x", "mm", 0.0, 5.0, 32)
ys = LineGenerator("y", "mm", 0.0, 2.0, 16)
gen = CompoundGenerator([ys, xs], [], [], duration=0.01)
gen.prepare()
env = make_env()

det = env.main_detector
duration = gen.get_point(0).duration


async def configure_detector():
    await det.exposure_time.put(duration)
    await det.array_counter.put(0)


async def configure_motors():
    first = gen.get_point(0)
    await move_to_point(env.axes, first)


async def configure_triggers():
    await env.trigger_box.min_seconds_between_checks.put(0.005)
    readout = env.sample_stage.x.position
    trigger = env.main_detector.acquire
    await env.trigger_box.trigger_1.input.put(readout)
    await env.trigger_box.trigger_1.output.put(trigger)


async def move_to_point(axes, point):
    for axis, pos in point.positions.items():
        motor = axes[axis]
        current_pos = (await motor.position.get()).value
        max_vel = (await motor.max_velocity.get()).value
        vel = abs(pos - current_pos) / point.duration
        if vel > max_vel:
            vel = max_vel
        await motor.velocity.put(vel)
        await motor.complete_move(pos)


async def run():
    print('Starting scan')
    for point in gen.iterator():
        print('Scanning point')
        trigger = env.trigger_box.trigger_1
        await trigger.min_value.put(point.lower['x'])
        await trigger.max_value.put(point.upper['x'])
        await move_to_point(env.axes, point)


async def test():
    await configure_detector()
    await configure_motors()
    await configure_triggers()
    await run()

job = test()
loop = asyncio.get_event_loop()
loop.create_task(job)
loop.run_forever()
#  TODO: Move things in parallel like malcolm, use enums like malcolm
