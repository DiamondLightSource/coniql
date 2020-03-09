from coniql.deviceplugin import DevicePlugin
from device.core.yaml.yamltype import yaml_load


def adsim_device_environment():
    beamline = adsim_environment('ws415')

    plugin = DevicePlugin()
    plugin.register_device(beamline, name='beamline')

    plugin.debug()
    return plugin


def adsim_environment(machine_name: str):
    path = 'protocol/beamline/beamlines/adsim/adsim.yaml'
    beamline = yaml_load(path, machine=machine_name)
    return beamline
