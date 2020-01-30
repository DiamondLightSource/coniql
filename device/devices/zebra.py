from dataclasses import dataclass

from device.devicetypes.channel import ReadWriteChannel
from device.util import await_value


@dataclass
class PositionCapture:
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
    arm_out: ReadWriteChannel[bool]
    pulse_source: ReadWriteChannel[str]
    pulse_input: ReadWriteChannel[str]
    pulse_max: ReadWriteChannel[int]


@dataclass
class Pulse:
    input: ReadWriteChannel[int]
    delay: ReadWriteChannel[float]
    width: ReadWriteChannel[float]
    time_units: ReadWriteChannel[str]


@dataclass
class ZebraIO:
    ttl_out_1: ReadWriteChannel[int]
    ttl_out_2: ReadWriteChannel[int]
    ttl_out_3: ReadWriteChannel[int]
    ttl_out_4: ReadWriteChannel[int]

    enc_copy_1: ReadWriteChannel[int]
    enc_copy_2: ReadWriteChannel[int]
    enc_copy_3: ReadWriteChannel[int]
    enc_copy_4: ReadWriteChannel[int]


@dataclass
class Zebra:
    position_capture: PositionCapture
    io: ZebraIO
    system_reset_process: ReadWriteChannel[int]

    def arm(self):
        await self.system_reset_process.put(1)
        await self.position_capture.arm.put(1)
        await await_value(self.position_capture.arm_out, 1)

    def disarm(self):
        await self.position_capture.disarm.put(1)
