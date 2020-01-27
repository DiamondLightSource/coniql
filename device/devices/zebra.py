from dataclasses import dataclass

from device.devicetypes.channel import ReadWriteChannel
from device.util import await_value


@dataclass
class PositionCapture:
    enc: ReadWriteChannel[int]
    dir: ReadWriteChannel[int]
    arm_source: ReadWriteChannel[int]
    gate_source: ReadWriteChannel[int]
    gate_input: ReadWriteChannel[int]
    gate_start: ReadWriteChannel[float]
    gate_width: ReadWriteChannel[float]
    num_gates: ReadWriteChannel[int]
    arm: ReadWriteChannel[bool]
    disarm: ReadWriteChannel[bool]
    arm_out: ReadWriteChannel[bool]
    pulse_source: ReadWriteChannel[int]
    pulse_input: ReadWriteChannel[int]
    pulse_max: ReadWriteChannel[int]


@dataclass
class Pulse:
    input: ReadWriteChannel[int]
    delay: ReadWriteChannel[float]
    width: ReadWriteChannel[float]
    time_units: ReadWriteChannel[int]


@dataclass
class Zebra:
    position_capture: PositionCapture

    # TODO: Investigate lists in device layer...?

    ttl_out_1: ReadWriteChannel[int]
    ttl_out_2: ReadWriteChannel[int]
    ttl_out_3: ReadWriteChannel[int]
    ttl_out_4: ReadWriteChannel[int]

    enc_copy_1: ReadWriteChannel[int]
    enc_copy_2: ReadWriteChannel[int]
    enc_copy_3: ReadWriteChannel[int]
    enc_copy_4: ReadWriteChannel[int]

    system_reset_process: ReadWriteChannel[int]

    def arm(self):
        await self.system_reset_process.put(1)
        await self.position_capture.arm.put(1)
        await await_value(self.position_capture.arm_out, 1)

    def disarm(self):
        await self.position_capture.disarm.put(1)
