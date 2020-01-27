from device.devicetypes.channel import ReadWriteChannel, ReadOnlyChannel


class Camera:
    exposure_time: ReadWriteChannel[float]
    acquire_period: ReadWriteChannel[float]
    exposures_per_image: ReadWriteChannel[int]
    number_of_images: ReadWriteChannel[int]
    image_mode: ReadWriteChannel[int]
    trigger_mode: ReadWriteChannel[int]
    acquire: ReadWriteChannel[bool]
    array_counter: ReadWriteChannel[int]
    framerate: ReadOnlyChannel[float]
