import asyncio

from scanpointgenerator import LineGenerator, CompoundGenerator

from beamline.beamlines.trainingrig import p47_environment
from device.pmacutil.pmacchildpart import PmacChildPart
from device.pmacutil.pmactrajectorypart import PmacTrajectoryPart

env = asyncio.run(p47_environment())

xs = LineGenerator("x", "mm", 0.0, 20.0, 8)
ys = LineGenerator("a", "mm", 0.0, 360.0, 4)
gen = CompoundGenerator([xs, ys], [], [])


async def job():
    pmac = env.pmac
    child_part = PmacChildPart(PmacTrajectoryPart(pmac), pmac)
    gen.prepare()
    num_points = len(list(gen.iterator()))
    await child_part.on_configure(0, num_points, None, gen, ['x', 'a'])
    await child_part.on_run()

asyncio.run(job())
