import dataclasses
from collections import Coroutine
from typing import Dict, Callable

from coniql.deviceplugin import DevicePlugin
from device.channel.ca import channel as cachannel, cabool, caenum
from device.channel.inmemory.channel import InMemoryReadOnlyChannel, \
    InMemoryReadWriteChannel
from device.devices.adcore.pos import PosPlugin
from device.devices.camera import Camera, DetectorDriver
from device.devices.faketriggerbox import in_memory_box, FakeTriggerBox
from device.devices.goniometer import Goniometer
from device.devices.motor import Motor
from device.devices.stage3d import Stage3D
from device.util import asyncio_gather_values


def mock_device_environment() -> DevicePlugin:
    def mock_motor(position: float = 0.0) -> Motor:
        return Motor(
            position=InMemoryReadOnlyChannel(position),
            setpoint=InMemoryReadWriteChannel(position),
            p=InMemoryReadWriteChannel(1.0),
            i=InMemoryReadWriteChannel(0.0),
            d=InMemoryReadWriteChannel(0.0),
            jog_positive=InMemoryReadWriteChannel(False),
            jog_negative=InMemoryReadWriteChannel(False),
            step_length=InMemoryReadWriteChannel(1.0),
            velocity=InMemoryReadWriteChannel(1.0),
            min=InMemoryReadWriteChannel(-1000.0),
            max=InMemoryReadWriteChannel(1000.0)
        )

    goniometer = Goniometer(
        omega=mock_motor(),
        chi=mock_motor(),
        phi=mock_motor(),
        sample=Stage3D(
            x=mock_motor(),
            y=mock_motor(),
            z=mock_motor()
        )
    )

    plugin = DevicePlugin()
    plugin.register_device(goniometer, name='goniometer')

    plugin.debug()
    return plugin


def adsim_device_environment():
    beamline = adsim_environment()

    plugin = DevicePlugin()
    plugin.register_device(beamline, name='beamline')

    plugin.debug()
    return plugin


async def adsim_environment():
    x = await motor('ws415-MO-SIM-01:M1')
    y = await motor('ws415-MO-SIM-01:M2')
    z = await motor('ws415-MO-SIM-01:M3')
    sample_stage = Stage3D(x, y, z)
    det = await camera('ws415-AD-SIM-01:CAM')
    trigger_box = in_memory_box()
    beamline = AdSimBeamline(
        trigger_box=trigger_box,
        detector=det,
        stage=sample_stage
    )
    return beamline

_CHANNEL_COROS = Dict[str, Coroutine]


async def motor(prefix: str) -> _CHANNEL_COROS:
    return dict(
        position=cachannel.connect(f'{prefix}.RBV'),
        setpoint=cachannel.connect(f'{prefix}'),
        stationary=cabool.connect(f'{prefix}.DMOV'),
        p=cachannel.connect(f'{prefix}.PCOF'),
        i=cachannel.connect(f'{prefix}.ICOF'),
        d=cachannel.connect(f'{prefix}.DCOF'),
        jog_positive=cabool.connect(f'{prefix}.TWF'),
        jog_negative=cabool.connect(f'{prefix}.TWR'),
        step_length=cachannel.connect(f'{prefix}.TWV'),
        velocity=cachannel.connect(f'{prefix}.VELO'),
        max_velocity=cachannel.connect(f'{prefix}.VMAX'),
        min=cachannel.connect(f'{prefix}.LLM'),
        max=cachannel.connect(f'{prefix}.HLM')
    )


async def camera(prefix: str) -> _CHANNEL_COROS:
    drv = await detector_driver(prefix)
    return dict(
        **drv,
        exposure_time=cachannel.connect(f'{prefix}:AcquireTime',
                                        rbv_suffix='_RBV'),
        acquire_period=cachannel.connect(f'{prefix}:AcquirePeriod',
                                         rbv_suffix='_RBV')
    )


async def detector_driver(prefix: str) -> _CHANNEL_COROS:
    return dict(
        exposures_per_image=cachannel.connect(f'{prefix}:NumExposures',
                                              rbv_suffix='_RBV'),
        number_of_images=cachannel.connect(f'{prefix}:NumImages',
                                           rbv_suffix='_RBV'),
        image_mode=caenum.connect(f'{prefix}:ImageMode',
                                  rbv_suffix='_RBV'),
        trigger_mode=caenum.connect(f'{prefix}:TriggerMode',
                                    rbv_suffix='_RBV'),
        acquire=cabool.connect(f'{prefix}:Acquire'),
        array_counter=cachannel.connect(f'{prefix}:ArrayCounter',
                                        rbv_suffix='_RBV'),
        framerate=cachannel.connect(f'{prefix}:ArrayRate_RBV')
    )


async def pos_plugin(prefix: str) -> _CHANNEL_COROS:
    return dict(

    )


async def ad_plugin(prefix: str) -> _CHANNEL_COROS:
    return dict(
        array_port=cachannel.connect()
    )


async def build_from_coros(coros: _CHANNEL_COROS, device_constructor: Callable):
    channels = await asyncio_gather_values(coros)
    return device_constructor(**channels)


@dataclasses.dataclass
class AdSimBeamline:
    trigger_box: FakeTriggerBox
    detector: Camera
    stage: Stage3D
