from typing_extensions import Protocol

from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel


class DetectorDriver(Protocol):
    exposures_per_image: ReadWriteChannel[int]
    number_of_images: ReadWriteChannel[int]
    image_mode: ReadWriteChannel[str]
    trigger_mode: ReadWriteChannel[str]
    acquire: ReadWriteChannel[bool]
    array_counter: ReadWriteChannel[int]
    framerate: ReadOnlyChannel[float]


class DutyCyclable(Protocol):
    exposure_time: ReadWriteChannel[float]
    acquire_period: ReadWriteChannel[float]


class Camera(DutyCyclable, DetectorDriver, Protocol):
    pass
