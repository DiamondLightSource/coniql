from device.channel.ca.bool import CaBool
from device.channel.ca.channel import CaChannel
from device.channel.ca.enum import CaEnum
from device.channel.ca.string import CaString
from device.pmac.protocol.pmac import ProfileBuild, ProfilePart, Axis, Axes, \
    TrajectoryScanStatus, TrajDriverStatus, PmacTrajectory, Pmac, PmacMotors


def profile_build(prefix: str) -> ProfileBuild:
    return ProfileBuild(
        **profile_part_layout(f'{prefix}:ProfileBuild'),

        max_points=CaChannel(f'{prefix}:ProfileNumPoints', rbv_suffix='_RBV'),
        num_points_to_build=CaChannel(f'{prefix}:ProfilePointsToBuild',
                                      rbv_suffix='_RBV'),
        time_array=CaChannel(f'{prefix}:ProfileTimeArray'),
        velocity_mode=CaChannel(f'{prefix}:VelocityMode'),
        user_programs=CaChannel(f'{prefix}:UserArray')
    )


def points_append(prefix: str) -> ProfilePart:
    return profile_part(f'{prefix}:ProfileAppend')


def profile_execution(prefix: str) -> ProfilePart:
    return profile_part(f'{prefix}:ProfileExecute')


def profile_part(prefix: str) -> ProfilePart:
    return ProfilePart(
        **profile_part_layout(prefix)
    )


def profile_part_layout(prefix: str):
    return dict(
        trigger=CaEnum(f'{prefix}', timeout=None),
        status=CaString(f'{prefix}Status_RBV'),
        state=CaString(f'{prefix}State_RBV'),
        message=CaString(f'{prefix}Message_RBV')
    )


def axis(prefix: str) -> Axis:
    return Axis(
        use=CaBool(f'{prefix}:UseAxis'),
        num_points=CaChannel(f'{prefix}:NoOfPts'),
        max_points=CaChannel(f'{prefix}:Positions.NELM'),
        positions=CaChannel(f'{prefix}:Positions')
    )


def axes(prefix: str) -> Axes:
    return Axes(
        a=axis(f'{prefix}:A'),
        b=axis(f'{prefix}:B'),
        c=axis(f'{prefix}:C'),
        u=axis(f'{prefix}:U'),
        v=axis(f'{prefix}:V'),
        w=axis(f'{prefix}:W'),
        x=axis(f'{prefix}:X'),
        y=axis(f'{prefix}:Y'),
        z=axis(f'{prefix}:Z'),
    )


def trajectory_scan_status(prefix: str) -> TrajectoryScanStatus:
    return TrajectoryScanStatus(
        buffer_a_address=CaString(f'{prefix}:BufferAAddress_RBV'),
        buffer_b_address=CaString(f'{prefix}:BufferBAddress_RBV'),
        num_points_in_buffer=CaChannel(f'{prefix}:BufferLength_RBV'),
        current_buffer=CaString(f'{prefix}:CurrentBuffer_RBV'),
        current_index=CaChannel(f'{prefix}:CurrentIndex_RBV'),
        points_scanned=CaChannel(f'{prefix}:TotalPoints_RBV'),
        status=CaChannel(f'{prefix}:TrajectoryStatus_RBV'),
    )


def trajectory_driver_status(prefix: str) -> TrajDriverStatus:
    return TrajDriverStatus(
        driver_a_index=CaChannel(f'{prefix}:EpicsBufferAPtr_RBV'),
        driver_b_index=CaChannel(f'{prefix}:EpicsBufferBPtr_RBV'),
        num_points_in_scan=CaChannel(f'{prefix}:ProfilePointsBuilt_RBV'),
        scan_time=CaChannel(f'{prefix}:TscanTime_RBV'),
        coordinate_system=CaChannel(f'{prefix}:TscanCs_RBV'),
        status=CaChannel(f'{prefix}:TscanExtStatus_RBV'),
    )


def trajectory(prefix: str) -> PmacTrajectory:
    return PmacTrajectory(
        profile_build=profile_build(prefix),
        points_append=points_append(prefix),
        profile_execution=profile_execution(prefix),
        axes=axes(prefix),
        scan_status=trajectory_scan_status(prefix),
        driver_status=trajectory_driver_status(prefix),
        program_version=CaChannel(f'{prefix}:ProgramVersion_RBV'),
        percentage_complete=CaChannel(f'{prefix}:TscanPercent_RBV'),
        profile_abort=CaBool(f'{prefix}:ProfileAbort'),
        coordinate_system_name=CaEnum(f'{prefix}:ProfileCsName', rbv_suffix='_RBV')
    )


def pmac(prefix: str, motors: PmacMotors) -> Pmac:
    return Pmac(
        i10=CaChannel(f'{prefix}:I10'),
        trajectory=trajectory(prefix),
        motors=motors
    )
