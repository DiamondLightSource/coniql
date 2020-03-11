from coniql.devicelayer.deviceplugin import DeviceLayer
from device.beamline.adsim import AdSimBeamline


def adsim_device_environment(machine: str):
    beamline = adsim_environment(machine)
    layer = DeviceLayer.from_tree(beamline)
    return layer


def adsim_environment(machine: str):
    beamline = AdSimBeamline(machine=machine)
    return beamline
