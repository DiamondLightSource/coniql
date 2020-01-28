import numpy as np
import asyncio

from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass, asdict

from scanpointgenerator import Point, LineGenerator, CompoundGenerator

from beamline.scheme.scheme import Scheme, ArmedScheme
from coniql.deviceplugin import adsim_environment
from device.devices.camera import Camera
from device.devices.faketriggerbox import FakeTriggerBox
from device.devices.positioner import Positioner, PositionerWithStatus
from device.devices.stage3d import Stage3D
from device.util import put_all


def exposure_delay(exposure_time: float, acquire_period: float) -> float:
    readout_time = acquire_period - exposure_time
    return readout_time / 2


@dataclass
class AdSimScanEnvironment:
    trigger_box: FakeTriggerBox
    main_detector: Camera
    secondary_detector: Optional[Camera]
    sample_stage: Stage3D
    axes: Dict[str, PositionerWithStatus]


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
    for axis, pos in point.positions.items():
        await axes[axis].complete_move(pos)


async def run(env: AdSimScanEnvironment, scan_point_generator):
    scan_point_generator.prepare()
    print('Starting scan')
    for point in scan_point_generator.iterator():
        print('Scanning point')
        await move_to_point(env.axes, point)
        await env.main_detector.acquire.put(True)


async def test(env: AdSimScanEnvironment, scan_point_generator):
    await prepare_detector(env)
    await configure_stage(env, scan_point_generator)
    await run(env, scan_point_generator)


main_env = adsim_environment()
env = AdSimScanEnvironment(
    trigger_box=main_env.trigger_box,
    main_detector=main_env.detector,
    secondary_detector=None,
    sample_stage=main_env.stage,
    axes={
        'x': main_env.stage.x,
        'y': main_env.stage.y
    }
)

xs = LineGenerator("x", "mm", 0.0, 5.0, 32)
ys = LineGenerator("y", "mm", 0.0, 2.0, 16)
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


