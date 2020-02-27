import asyncio

from scanpointgenerator import LineGenerator, CompoundGenerator

from beamline.beamlines.trainingrig import p49_environment, p47_environment
from device.pmacutil.pmacchildpart import configure_pmac_for_scan, \
    TrajectoryModel, validate_trajectory_scan

env = asyncio.run(p49_environment())

xs = LineGenerator("x", "mm", 1.0, 2.0, 8)
ys = LineGenerator("a", "mm", 5.0, 15.0, 4)
gen = CompoundGenerator([xs, ys], [], [], duration=0.5)


async def job():
    pmac = env.pmac
    gen.prepare()

    model = TrajectoryModel.all_steps(gen)

    revised_generator = await validate_trajectory_scan(pmac, model)
    if revised_generator is not None:
        revised_generator.prepare()
        model.generator = revised_generator

    await configure_pmac_for_scan(pmac, model)
    await pmac.trajectory.execute_profile()
    # await child_part.on_configure(0, num_points, None, gen, ['x', 'a'])
    # await child_part.on_run()

    # print(f'ptb: {await pmac.trajectory.profile_build.num_points_to_build.get()}')
    # await pa(pmac.trajectory.profile_build.time_array, 'time')
    # await pa(pmac.trajectory.profile_build.velocity_mode, 'vmode')
    # await pa(pmac.trajectory.profile_build.user_programs, 'userp')
    # await pa(pmac.trajectory.axes.a.positions, 'a')
    # await pa(pmac.trajectory.axes.x.positions, 'x')



async def pa(chan, name):
    arr = await chan.get()
    print(f'{name}, length={len(arr)}: {arr}')

asyncio.run(job())
