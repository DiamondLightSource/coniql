from device.pmac.protocol.pmac import Trajectory


async def build_profile(traj: Trajectory):
    await traj.profile_build.trigger.put('Build')


async def append_points(traj: Trajectory):
    await traj.points_append.trigger.put('Append')


async def execute_profile(traj: Trajectory):
    await traj.profile_execution.trigger.put('Execute')


async def abort(traj: Trajectory):
    await traj.profile_abort.put(False)
