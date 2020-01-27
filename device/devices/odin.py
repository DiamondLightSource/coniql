from dataclasses import dataclass

from device.devices.camera import Camera
from device.devicetypes.channel import ReadWriteChannel, ReadOnlyChannel


@dataclass
class OdinDetector(Camera):
    file_path: ReadWriteChannel[str]
    file_path_exists: ReadOnlyChannel[bool]
    name_pattern: ReadWriteChannel[str]
    sequence_id: ReadOnlyChannel[int]
