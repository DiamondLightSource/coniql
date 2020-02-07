from dataclasses import dataclass

from coniql.deviceplugin import DevicePlugin
from device.devices.addetector import AdDetector
from device.devices.camera import Camera
from device.devices.faketriggerbox import in_memory_box, FakeTriggerBox
from device.devices.stage3d import Stage3D
from device.epics.ad import camera
from device.epics.addets import ad_detector
from device.epics.motor import motor


def adsim_device_environment():
    beamline = adsim_environment('ws415')

    plugin = DevicePlugin()
    plugin.register_device(beamline, name='beamline')

    plugin.debug()
    return plugin


@dataclass
class AdSimBeamline:
    trigger_box: FakeTriggerBox
    detector: AdDetector
    stage: Stage3D


async def adsim_environment(machine_name: str) -> AdSimBeamline:
    x = await motor(f'{machine_name}-MO-SIM-01:M1')
    y = await motor(f'{machine_name}-MO-SIM-01:M2')
    z = await motor(f'{machine_name}-MO-SIM-01:M3')
    sample_stage = Stage3D(x, y, z)
    det = await ad_detector(f'{machine_name}-AD-SIM-01')
    trigger_box = in_memory_box()
    beamline = AdSimBeamline(
        trigger_box=trigger_box,
        detector=det,
        stage=sample_stage
    )
    return beamline
