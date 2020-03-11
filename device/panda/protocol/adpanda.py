from typing_extensions import Protocol

from device.adcore.camera import DetectorDriver
from device.adcore.hdf import HdfPlugin


class AdPandA(Protocol):
    driver: DetectorDriver
    # pos: PosPlugin
    hdf: HdfPlugin
