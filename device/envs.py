import dataclasses

from coniql.deviceplugin import DevicePlugin
from device.channel.inmemory.channel import InMemoryReadOnlyChannel, \
    InMemoryReadWriteChannel
from device.devices.camera import Camera
from device.devices.faketriggerbox import in_memory_box, FakeTriggerBox
from device.devices.goniometer import Goniometer
from device.devices.motor import Motor
from device.devices.stage3d import Stage3D
from device.epics.ad import camera
from device.epics.motor import motor


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


@dataclasses.dataclass
class AdSimBeamline:
    trigger_box: FakeTriggerBox
    detector: Camera
    stage: Stage3D
