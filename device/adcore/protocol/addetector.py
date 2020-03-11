from typing_extensions import Protocol

from device.adcore.protocol.hdf import HdfPlugin
from device.adcore.protocol.camera import Camera


class AdDetector(Protocol):
    camera: Camera
    hdf: HdfPlugin
