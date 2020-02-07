from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel, WriteableChannel
from device.devices.adcore.plugin import AdPlugin


@dataclass
class Swmr:
    mode: ReadWriteChannel[str]
    active: ReadWriteChannel[bool]
    position_mode: ReadWriteChannel[str]
    flush: WriteableChannel[bool]
    flush_on_nth_frame: ReadWriteChannel[int]
    nd_attribute_flush: ReadWriteChannel[int]

    async def flush_now(self):
        await self.flush.put(True)


@dataclass
class HdfPlugin(AdPlugin):
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

    async def arm(self):
        await self.capture.put(True)
        armed = await self.capture.get()
        if not armed:
            error_message = await self.write_status_message.get()
            raise ValueError(f'Could not arm HDF5 plugin, error was {error_message}')

    async def disarm(self):
        await self.capture.put(False)
