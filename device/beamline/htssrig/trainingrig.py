from coniql.devicelayer.deviceplugin import DeviceLayer
from device.beamline.htssrig import HtssRig


def htss_environment(beamline_prefix: str):
    beamline = training_rig_environment(beamline_prefix)
    layer = DeviceLayer.from_tree(beamline)
    return layer


def training_rig_environment(beamline_prefix: str):
    beamline = HtssRig(rig=beamline_prefix)
    return beamline
