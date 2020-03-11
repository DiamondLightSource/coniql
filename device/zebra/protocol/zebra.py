from typing_extensions import Protocol

from device.channel.channeltypes.channel import ReadWriteChannel


class PositionCapture(Protocol):
    enc: ReadWriteChannel[str]
    dir: ReadWriteChannel[str]
    arm_source: ReadWriteChannel[str]
    gate_source: ReadWriteChannel[str]
    gate_input: ReadWriteChannel[str]
    gate_start: ReadWriteChannel[float]
    gate_width: ReadWriteChannel[float]
    num_gates: ReadWriteChannel[int]
    arm: ReadWriteChannel[bool]
    disarm: ReadWriteChannel[bool]
    arm_status: ReadWriteChannel[bool]
    pulse_source: ReadWriteChannel[str]
    pulse_input: ReadWriteChannel[str]
    pulse_max: ReadWriteChannel[int]


class Pulse(Protocol):
    input: ReadWriteChannel[int]
    delay: ReadWriteChannel[float]
    width: ReadWriteChannel[float]
    time_units: ReadWriteChannel[str]


class ZebraIO(Protocol):
    ttl_out_1: ReadWriteChannel[int]
    ttl_out_2: ReadWriteChannel[int]
    ttl_out_3: ReadWriteChannel[int]
    ttl_out_4: ReadWriteChannel[int]

    enc_copy_1: ReadWriteChannel[int]
    enc_copy_2: ReadWriteChannel[int]
    enc_copy_3: ReadWriteChannel[int]
    enc_copy_4: ReadWriteChannel[int]


class Zebra(Protocol):
    position_capture: PositionCapture
    io: ZebraIO
    system_reset_process: ReadWriteChannel[int]
