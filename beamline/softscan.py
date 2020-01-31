import asyncio
from typing import Dict

from scanpointgenerator import Point, LineGenerator, CompoundGenerator

from beamline.scanenv import AdSimScanEnvironment, make_env
from device.devices.positioner import PositionerWithStatus


def exposure_delay(exposure_time: float, acquire_period: float) -> float:
    readout_time = acquire_period - exposure_time
    return readout_time / 2


async def prepare_detector(env: AdSimScanEnvironment):
    print('Preparing detector')
    await env.main_detector.array_counter.put(0)


async def configure_stage(env: AdSimScanEnvironment, scan_point_generator):
    stage = env.sample_stage
    scan_point_generator.prepare()
    first = scan_point_generator.get_point(0)
    print('Moving to starting position')
    await move_to_point(env.axes, first)


async def move_to_point(axes: Dict[str, PositionerWithStatus], point: Point):
    moves = [axes[axis].complete_move(pos)
             for axis, pos in point.positions.items()]
    return await asyncio.wait(moves)


async def run(env: AdSimScanEnvironment, scan_point_generator):
    scan_point_generator.prepare()
    print('Starting scan')
    for point in scan_point_generator.iterator():
        print('Scanning point')
        await move_to_point(env.axes, point)
        await env.main_detector.acquire.put(True)
        await asyncio.sleep(0.1)


async def test(env: AdSimScanEnvironment, scan_point_generator):
    await prepare_detector(env)
    await configure_stage(env, scan_point_generator)
    await run(env, scan_point_generator)


env = make_env()

xs = LineGenerator("x", "mm", 0.0, 20.0, 8)
ys = LineGenerator("y", "mm", 0.0, 30.0, 4)
gen = CompoundGenerator([xs, ys], [], [])


job = test(env, gen)

asyncio.run(job)

# class AdSimTriggeringSchemePre:
#     async def prepare(self) -> ArmedScheme:
#         await self.trigger_box.min_seconds_between_checks.put(0.01)
#         readout = self.sample_stage.x.position
#         trigger = self.main_detector.acquire
#         await self.trigger_box.trigger_1.input.put(readout)
#         await self.trigger_box.trigger_1.output.put(trigger)
#
#         exposure_time = await self.main_detector.exposure_time.get()
#         acquire_period = await self.main_detector.acquire_period.get()
#         delay = exposure_delay(exposure_time.value, acquire_period.value)
#         await self.trigger_box.trigger_1.delay_seconds.put(delay)
