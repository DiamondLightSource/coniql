import dataclasses

from coniql.deviceplugin import DevicePlugin
from device.channel.ca.cabool import CaBool
from device.channel.ca.caenum import CaEnum
from device.channel.ca.channel import CaChannel
from device.channel.inmemory.channel import InMemoryReadOnlyChannel, \
    InMemoryReadWriteChannel
from device.devices.camera import Camera
from device.devices.faketriggerbox import in_memory_box, FakeTriggerBox
from device.devices.goniometer import Goniometer
from device.devices.motor import Motor
from device.devices.stage3d import Stage3D


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

def adsim_environment():
    def motor(prefix: str) -> Motor:
        return Motor(
            position=CaChannel(f'{prefix}.RBV'),
            setpoint=CaChannel(f'{prefix}'),
            stationary=CaChannel(f'{prefix}.DMOV'),
            p=CaChannel(f'{prefix}.PCOF'),
            i=CaChannel(f'{prefix}.ICOF'),
            d=CaChannel(f'{prefix}.DCOF'),
            jog_positive=CaBool(f'{prefix}.TWF'),
            jog_negative=CaBool(f'{prefix}.TWR'),
            step_length=CaChannel(f'{prefix}.TWV'),
            velocity=CaChannel(f'{prefix}.VELO'),
            max_velocity=CaChannel(f'{prefix}.VMAX'),
            min=CaChannel(f'{prefix}.LLM'),
            max=CaChannel(f'{prefix}.HLM')
        )

    def camera(prefix: str) -> Camera:
        return Camera(
            exposure_time=CaChannel(f'{prefix}:AcquireTime',
                                             rbv_suffix='_RBV'),
            acquire_period=CaChannel(f'{prefix}:AcquirePeriod',
                                              rbv_suffix='_RBV'),
            exposures_per_image=CaChannel(f'{prefix}:NumExposures',
                                                   rbv_suffix='_RBV'),
            number_of_images=CaChannel(f'{prefix}:NumImages',
                                                rbv_suffix='_RBV'),
            image_mode=CaEnum(f'{prefix}:ImageMode',
                                          rbv_suffix='_RBV'),
            trigger_mode=CaEnum(f'{prefix}:TriggerMode',
                                            rbv_suffix='_RBV'),
            acquire=CaBool(f'{prefix}:Acquire'),
            array_counter=CaChannel(f'{prefix}:ArrayCounter',
                                             rbv_suffix='_RBV'),
            framerate=CaChannel(f'{prefix}:ArrayRate_RBV')
        )

    x = motor('ws415-MO-SIM-01:M1')
    y = motor('ws415-MO-SIM-01:M2')
    z = motor('ws415-MO-SIM-01:M3')
    sample_stage = Stage3D(x, y, z)
    det = camera('ws415-AD-SIM-01:CAM')
    trigger_box = in_memory_box()
    beamline = AdSimBeamline(
        trigger_box=trigger_box,
        detector=det,
        stage=sample_stage
    )
    return beamline


@dataclasses.dataclass
class AdSimBeamline:
    trigger_box: FakeTriggerBox
    detector: Camera
    stage: Stage3D
