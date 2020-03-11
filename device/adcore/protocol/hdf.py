from typing_extensions import Protocol

from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel, CanPutValue
from device.adcore.protocol.plugin import AdPlugin


class Swmr(Protocol):
    mode: ReadWriteChannel[str]
    active: ReadWriteChannel[bool]
    position_mode: ReadWriteChannel[str]
    flush: CanPutValue[bool]
    flush_on_nth_frame: ReadWriteChannel[int]
    nd_attribute_flush: ReadWriteChannel[int]


class HdfPlugin(AdPlugin, Protocol):
    file_path: ReadWriteChannel[str]
    file_name: ReadWriteChannel[str]
    suffix: ReadWriteChannel[str]

    next_file_number: ReadWriteChannel[int]
    file_name_format: ReadWriteChannel[str]
    num_to_capture: ReadWriteChannel[int]
    num_captured: ReadOnlyChannel[int]
    auto_increment: ReadWriteChannel[str]
    file_format: ReadWriteChannel[str]
    auto_save: ReadWriteChannel[str]

    capture_mode: ReadWriteChannel[str]
    capture: ReadWriteChannel[bool]
    write_status: ReadOnlyChannel[bool]
    write_status_message: ReadOnlyChannel[str]
    full_file_name: ReadOnlyChannel[str]

    num_extra_dims: ReadWriteChannel[int]
    num_chunk_rows: ReadWriteChannel[int]

    swmr: Swmr
