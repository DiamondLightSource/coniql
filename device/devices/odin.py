from dataclasses import dataclass

from device.devicetypes.channel import ReadWriteChannel, ReadOnlyChannel


@dataclass
class OdinDetector:
    exposure_time: ReadWriteChannel[float]
    acquire_period: ReadWriteChannel[float]
    exposures_per_image: ReadWriteChannel[int]
    number_of_images: ReadWriteChannel[int]
    image_mode: ReadWriteChannel[int]
    trigger_mode: ReadWriteChannel[int]
    acquire: ReadWriteChannel[bool]
    array_counter: ReadWriteChannel[int]
    framerate: ReadOnlyChannel[float]

    file_path: ReadWriteChannel[str]
    file_path_exists: ReadOnlyChannel[bool]
    name_pattern: ReadWriteChannel[str]
    sequence_id: ReadOnlyChannel[int]

