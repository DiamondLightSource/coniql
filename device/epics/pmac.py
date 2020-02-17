from device.channel.ca.cabool import CaBool
from device.channel.ca.channel import CaField
from device.devices.motor import Motor
from device.devices.pmac import ProfileBuild, ProfilePart, Axis, Axes, \
    TrajectoryScanStatus, TrajDriverStatus, PmacTrajectory, Pmac
from device.epics.util import device_from_layout, connect_channels
from device.util import asyncio_gather_values


async def profile_build(prefix: str) -> ProfileBuild:
    layout = profile_build_channels(prefix)
    return await device_from_layout(layout, ProfileBuild)


def profile_build_channels(prefix: str):
    return dict(
        max_points=CaField(f'{prefix}:ProfileNumPoints', rbv_suffix='_RBV'),
        num_points_to_build=CaField(f'{prefix}:ProfilePointsToBuild',
                                    rbv_suffix='_RBV'),
        **profile_part_channels(f'{prefix}:ProfileBuild')
    )


async def points_append(prefix: str) -> ProfilePart:
    layout = points_append_channels(prefix)
    return await device_from_layout(layout, ProfilePart)


def points_append_channels(prefix: str):
    return profile_part_channels(f'{prefix}:ProfileAppend')


async def profile_execution(prefix: str) -> ProfilePart:
    layout = profile_execution_channels(prefix)
    return await device_from_layout(layout, ProfilePart)


def profile_execution_channels(prefix: str):
    return profile_part_channels(f'{prefix}:ProfileExecute')


def profile_part_channels(prefix: str):
    return dict(
        trigger=CaBool(f'{prefix}'),
        status=CaField(f'{prefix}Status_RBV'),
        state=CaField(f'{prefix}State_RBV'),
        message=CaField(f'{prefix}Message_RBV')
    )


async def axis(prefix: str) -> Axis:
    layout = profile_build_channels(prefix)
    return await device_from_layout(layout, Axis)


def axis_channels(prefix: str):
    return dict(
        use=CaBool(f'{prefix}:UseAxis'),
        num_points=CaField(f'{prefix}:NoOfPts'),
        max_points=CaField(f'{prefix}:Positions.NELM')
    )


async def axes(prefix: str) -> Axes:
    children = await asyncio_gather_values(dict(
        a=axis(f'{prefix}:A'),
        b=axis(f'{prefix}:B'),
        c=axis(f'{prefix}:C'),
        u=axis(f'{prefix}:D'),
        v=axis(f'{prefix}:E'),
        w=axis(f'{prefix}:F'),
        x=axis(f'{prefix}:G'),
        y=axis(f'{prefix}:H'),
        z=axis(f'{prefix}:I'),
    ))
    return Axes(**children)


async def trajectory_scan_status(prefix: str) -> TrajectoryScanStatus:
    layout = trajectory_scan_status_channels(prefix)
    return await device_from_layout(layout, TrajectoryScanStatus)


def trajectory_scan_status_channels(prefix: str):
    return dict(
        buffer_a_address=CaField(f'{prefix}:BufferAAddress_RBV'),
        buffer_b_address=CaField(f'{prefix}:BufferBAddress_RBV'),
        num_points_in_buffer=CaField(f'{prefix}:BufferLength_RBV'),
        current_buffer=CaField(f'{prefix}:CurrentBuffer_RBV'),
        current_index=CaField(f'{prefix}:CurrentIndex_RBV'),
        points_scanned=CaField(f'{prefix}:TotalPoints_RBV'),
        status=CaField(f'{prefix}:TrajectoryStatus_RBV'),
    )


async def trajectory_driver_status(prefix: str) -> TrajDriverStatus:
    layout = trajectory_driver_status_channels(prefix)
    return await device_from_layout(layout, TrajDriverStatus)


def trajectory_driver_status_channels(prefix: str):
    return dict(
        driver_a_index=CaField(f'{prefix}:EpicsBufferAPtr_RBV'),
        driver_b_index=CaField(f'{prefix}:EpicsBufferBPtr_RBV'),
        num_points_in_scan=CaField(f'{prefix}:ProfilePointsBuilt_RBV'),
        scan_time=CaField(f'{prefix}:TscanTime_RBV'),
        coordinate_system=CaField(f'{prefix}:TscanCs_RBV'),
        status=CaField(f'{prefix}:TscanExtStatus_RBV'),
    )


async def trajectory(prefix: str) -> PmacTrajectory:
    channels = await connect_channels(trajectory_channels(prefix))
    children = await asyncio_gather_values(dict(
        profile_build=profile_build(prefix),
        points_append=points_append(prefix),
        profile_execution=profile_execution(prefix),
        axes=axes(prefix),
        scan_status=trajectory_scan_status(prefix),
        driver_status=trajectory_driver_status(prefix),
        **channels
    ))
    return PmacTrajectory(**children)


def trajectory_channels(prefix: str):
    return dict(
        percentage_complete=CaField(f'{prefix}:TscanPercent_RBV'),
        profile_abort=CaBool(f'{prefix}:ProfileAbort')
    )


async def pmac(prefix: str) -> Pmac:
    channels = await connect_channels(pmac_channels(prefix))
    children = await asyncio_gather_values(dict(
        trajectory=trajectory(prefix),
        **channels
    ))
    return Pmac(**children)


def pmac_channels(prefix: str):
    return dict(
        i10=CaField(f'{prefix}:I10')
    )
