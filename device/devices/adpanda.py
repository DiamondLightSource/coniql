from dataclasses import dataclass

from device.devices.camera import DetectorDriver
from device.devices.adcore.pos import PosPlugin
from device.devices.adcore.hdf import HdfPlugin


@dataclass
class AdPandA:
    driver: DetectorDriver
    # pos: PosPlugin
    hdf: HdfPlugin
