import asyncio

from scanpointgenerator import LineGenerator, CompoundGenerator

from device.beamline.beamlines.trainingrig import p49_environment
from device.pmac.control.trajectorycontrol import scan_points
from device.pmac.control.trajectorymodel import TrajectoryModel

env = asyncio.run(p49_environment())

xs = LineGenerator("x", "mm", 1.0, 2.0, 8)
ys = LineGenerator("a", "mm", 5.0, 15.0, 4)
gen = CompoundGenerator([xs, ys], [], [], duration=0.5)


async def job():
    pmac = env.pmac
    gen.prepare()
    model = TrajectoryModel.all_steps(gen)
    await scan_points(pmac, model)
    # await child_part.on_configure(0, num_points, None, gen, ['x', 'a'])
    # await child_part.on_run()

    # print(f'ptb: {await pmac.control.profile_build.num_points_to_build.get()}')
    # await pa(pmac.control.profile_build.time_array, 'time')
    # await pa(pmac.control.profile_build.velocity_mode, 'vmode')
    # await pa(pmac.control.profile_build.user_programs, 'userp')
    # await pa(pmac.control.axes.a.positions, 'a')
    # await pa(pmac.control.axes.x.positions, 'x')



async def pa(chan, name):
    arr = await chan.get()
    print(f'{name}, length={len(arr)}: {arr}')

asyncio.run(job())
