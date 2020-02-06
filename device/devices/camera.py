from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadWriteChannel, ReadOnlyChannel


@dataclass
class DetectorDriver:
    exposures_per_image: ReadWriteChannel[int]
    number_of_images: ReadWriteChannel[int]
    image_mode: ReadWriteChannel[str]
    trigger_mode: ReadWriteChannel[str]
    acquire: ReadWriteChannel[bool]
    array_counter: ReadWriteChannel[int]
    framerate: ReadOnlyChannel[float]


@dataclass
class DutyCyclable:
    exposure_time: ReadWriteChannel[float]
    acquire_period: ReadWriteChannel[float]


class Camera(DetectorDriver, DutyCyclable):
    pass
