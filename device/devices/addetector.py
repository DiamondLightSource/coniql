from dataclasses import dataclass

from device.devices.adcore.hdf import HdfPlugin
from device.devices.camera import Camera


@dataclass
class AdDetector:
    camera: Camera
    hdf: HdfPlugin
