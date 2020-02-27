import asyncio

from scanpointgenerator import Point, LineGenerator, CompoundGenerator

from device.beamline.beamlines import p47_environment, TrainingRig


def exposure_delay(exposure_time: float, acquire_period: float) -> float:
    readout_time = acquire_period - exposure_time
    return readout_time / 2


async def prepare_detector(env: TrainingRig):
    print('Preparing detector')
    await env.detector.camera.array_counter.put(0)


async def configure_stage(env: TrainingRig, scan_point_generator):
    stage = env.sample_stage
    scan_point_generator.prepare()
    first = scan_point_generator.get_point(0)
    print('Moving to starting position')
    await move_to_point(env, first)


async def move_to_point(env: TrainingRig, point: Point):
    stage = env.sample_stage
    jobs = []
    for axis, pos in point.positions.items():
        motor = stage.__dict__[axis]
        jobs.append(motor.setpoint.put(pos))
    return await asyncio.wait(jobs)


async def run(env: TrainingRig, scan_point_generator):
    scan_point_generator.prepare()
    print('Starting scan')
    for point in scan_point_generator.iterator():
        print('Scanning point')
        await move_to_point(env, point)
        await env.detector.camera.acquire.put(True)
        await asyncio.sleep(0.1)


async def test(env: TrainingRig, scan_point_generator):
    await prepare_detector(env)
    await configure_stage(env, scan_point_generator)
    await run(env, scan_point_generator)


env = asyncio.run(p47_environment())

xs = LineGenerator("x", "mm", 0.0, 20.0, 8)
ys = LineGenerator("theta", "mm", 0.0, 360.0, 4)
gen = CompoundGenerator([xs, ys], [], [])


job = test(env, gen)

asyncio.run(job)
