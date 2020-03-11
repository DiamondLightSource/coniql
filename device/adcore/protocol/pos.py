from typing_extensions import Protocol

from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel
from device.adcore.protocol.plugin import AdPlugin


class PosPlugin(AdPlugin, Protocol):
    source_file: ReadWriteChannel[str]
    file_valid: ReadOnlyChannel[bool]

    running: ReadWriteChannel[bool]
    reset_running: ReadWriteChannel[bool]

    mode: ReadWriteChannel[str]
    num_positions: ReadOnlyChannel[int]
    delete: ReadWriteChannel[bool]
    current_index: ReadOnlyChannel[int]
    last_send_position: ReadOnlyChannel[int]  # ??

    num_missing_frames: ReadOnlyChannel[int]
    missing_frames_resetting: ReadWriteChannel[bool]

    num_duplicate_frames: ReadOnlyChannel[int]
    duplicate_frames_resetting: ReadWriteChannel[bool]

    next_expected_id: ReadWriteChannel[int]

    name_of_id_at: ReadWriteChannel[str]

    id_start_value: ReadWriteChannel[int]
    id_difference: ReadWriteChannel[int]
