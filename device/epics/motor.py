from device.channel.ca.cabool import CaBool
from device.channel.ca.channel import CaField
from device.channel.ca.caenum import CaEnum
from device.channel.ca.castring import CaString
from device.devices.motor import Motor
from device.epics.util import device_from_layout


async def motor(prefix: str) -> Motor:
    layout = motor_channels(prefix)
    return await device_from_layout(layout, Motor)


def motor_channels(prefix: str):
    return dict(
        **positioner_with_status_channels(prefix),
        p=CaField(f'{prefix}.PCOF'),
        i=CaField(f'{prefix}.ICOF'),
        d=CaField(f'{prefix}.DCOF'),
        jog_positive=CaBool(f'{prefix}.TWF'),
        jog_negative=CaBool(f'{prefix}.TWR'),
        step_length=CaField(f'{prefix}.TWV'),
        velocity=CaField(f'{prefix}.VELO'),
        max_velocity=CaField(f'{prefix}.VMAX'),
        min=CaField(f'{prefix}.LLM'),
        max=CaField(f'{prefix}.HLM'),
        acceleration_time=CaField(f'{prefix}.ACCL'),
        output=CaString(f'{prefix}.OUT'),
        resolution=CaField(f'{prefix}.MRES'),
        offset=CaField(f'{prefix}.OFF'),
        units=CaString(f'{prefix}.EGU'),
        cs_port=CaEnum(f'{prefix}:CsPort', rbv_suffix='_RBV'),
        cs_axis=CaString(f'{prefix}:CsAxis', rbv_suffix='_RBV'),
    )


def positioner_with_status_channels(prefix: str):
    return dict(
        position=CaField(f'{prefix}.RBV'),
        setpoint=CaField(f'{prefix}'),
        stationary=CaBool(f'{prefix}.DMOV')
    )
