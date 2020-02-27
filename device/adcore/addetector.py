from dataclasses import dataclass

from device.adcore.hdf import HdfPlugin
from device.adcore.camera import Camera


@dataclass
class AdDetector:
    camera: Camera
    hdf: HdfPlugin
