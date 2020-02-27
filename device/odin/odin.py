from dataclasses import dataclass

from device.adcore.camera import Camera
from device.channel.channeltypes.channel import ReadWriteChannel, ReadOnlyChannel


@dataclass
class OdinDetector(Camera):
    file_path: ReadWriteChannel[str]
    file_path_exists: ReadOnlyChannel[bool]
    name_pattern: ReadWriteChannel[str]
    sequence_id: ReadOnlyChannel[int]
