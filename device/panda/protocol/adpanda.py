from typing_extensions import Protocol

from device.adcore.protocol.camera import DetectorDriver
from device.adcore.protocol.hdf import HdfPlugin


class AdPandA(Protocol):
    driver: DetectorDriver
    # pos: PosPlugin
    hdf: HdfPlugin
