import asyncio

from dataclasses import dataclass

from coniql.deviceplugin import DevicePlugin
from device.channel.setup import setup
from device.adcore.addetector import AdDetector
from device.core.yamltype import yaml_load
from device.motor.stage3d import Stage3D
from device.epics.addets import ad_detector
from device.epics.motor import motor, scannable_motor


def adsim_device_environment():
    beamline = adsim_environment('ws415')

    plugin = DevicePlugin()
    plugin.register_device(beamline, name='beamline')

    plugin.debug()
    return plugin


@dataclass
class AdSimBeamline:
    # trigger_box: FakeTriggerBox
    detector: AdDetector
    stage: Stage3D


def adsim_environment(machine_name: str) -> AdSimBeamline:
    path = 'device/beamline/beamlines/adsim.yaml'
    beamline = yaml_load(path, machine=machine_name)
    asyncio.get_event_loop().create_task(setup(beamline))
    return beamline

    # x = scannable_motor(f'{machine_name}-MO-SIM-01:M1', 'x')
    # y = scannable_motor(f'{machine_name}-MO-SIM-01:M2', 'y')
    # z = scannable_motor(f'{machine_name}-MO-SIM-01:M3', 'z')
    # sample_stage = Stage3D(x, y, z)
    # det = ad_detector(f'{machine_name}-AD-SIM-01')
    # # trigger_box = in_memory_box()
    # beamline = AdSimBeamline(
    #     # trigger_box=trigger_box,
    #     detector=det,
    #     stage=sample_stage
    # )
    # await setup(beamline)
    # return beamline
