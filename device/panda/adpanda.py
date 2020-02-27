from dataclasses import dataclass

from device.adcore.camera import DetectorDriver
from device.adcore.hdf import HdfPlugin


@dataclass
class AdPandA:
    driver: DetectorDriver
    # pos: PosPlugin
    hdf: HdfPlugin
