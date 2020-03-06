from dataclasses import dataclass

from coniql.deviceplugin import DevicePlugin
from device.adcore.addetector import AdDetector
from device.core.yaml.yamltype import yaml_load
from device.motor.stage3d import Stage3D


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
    path = 'protocol/beamline/beamlines/adsim/adsim.yaml'
    beamline = yaml_load(path, machine=machine_name)
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
