from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadWriteChannel


@dataclass
class Bits:
    """Soft inputs and constant bits"""
    a: ReadWriteChannel[bool]
    b: ReadWriteChannel[bool]
    c: ReadWriteChannel[bool]
    d: ReadWriteChannel[bool]


@dataclass
class Output:
    out_units: ReadWriteChannel[str]
    out_scale: ReadWriteChannel[float]
    out_offset: ReadWriteChannel[float]
    out_capture: ReadWriteChannel[str]
    out_dataset_name: ReadWriteChannel[str]
    out_dataset_type: ReadWriteChannel[str]


@dataclass
class Calc(Output):
    inp_a: ReadWriteChannel[str]
    inp_b: ReadWriteChannel[str]
    inp_c: ReadWriteChannel[str]
    inp_d: ReadWriteChannel[str]

    type_a: ReadWriteChannel[str]
    type_b: ReadWriteChannel[str]
    type_c: ReadWriteChannel[str]
    type_d: ReadWriteChannel[str]

    func: ReadWriteChannel[str]


@dataclass
class Clock:
    period: ReadWriteChannel[float]
    period_units: ReadWriteChannel[str]


@dataclass
class Clocks:
    a: Clock
    b: Clock
    c: Clock
    d: Clock


@dataclass
class Counter(Output):
    enable: ReadWriteChannel[str]
    enable_delay: ReadWriteChannel[int]
    trig: ReadWriteChannel[str]
    trig_delay: ReadWriteChannel[int]
    dir: ReadWriteChannel[str]
    dir_delay: ReadWriteChannel[int]
    start: ReadWriteChannel[int]
    step: ReadWriteChannel[int]
    max: ReadWriteChannel[int]
    min: ReadWriteChannel[int]


@dataclass
class Div:
    enable: ReadWriteChannel[str]
    enable_delay: ReadWriteChannel[int]
    inp: ReadWriteChannel[str]
    inp_delay: ReadWriteChannel[int]
    divisor: ReadWriteChannel[int]
    first_pulse: ReadWriteChannel[str]


@dataclass
class Filter(Output):
    enable: ReadWriteChannel[str]
    enable_delay: ReadWriteChannel[int]
    trig: ReadWriteChannel[str]
    trig_delay: ReadWriteChannel[int]
    inp: ReadWriteChannel[str]
    mode: ReadWriteChannel[str]


@dataclass
class EncVal:
    units: ReadWriteChannel[str]
    scale: ReadWriteChannel[float]
    offset: ReadWriteChannel[float]
    capture: ReadWriteChannel[str]
    dataset_name: ReadWriteChannel[str]
    dataset_type: ReadWriteChannel[str]


@dataclass
class InEnc:
    clk: ReadWriteChannel[str]
    clk_delay: ReadWriteChannel[int]
    protocol: ReadWriteChannel[str]
    clk_src: ReadWriteChannel[str]
    clk_period: ReadWriteChannel[float]
    clk_period_units: ReadWriteChannel[str]
    bits: ReadWriteChannel[int]
    lsb_discard: ReadWriteChannel[int]
    msb_discard: ReadWriteChannel[int]
    setp: ReadWriteChannel[int]
    rst_on_z: ReadWriteChannel[bool]
    outputs: ReadWriteChannel[str]
    val: EncVal


@dataclass
class LutInput:
    soruce: ReadWriteChannel[str]
    delay: ReadWriteChannel[int]
    dtype: ReadWriteChannel[str]


@dataclass
class Lut:
    func: ReadWriteChannel[str]
    inp_a: LutInput
    inp_b: LutInput
    inp_c: LutInput
    inp_d: LutInput
    inp_e: LutInput


@dataclass
class Panda:
    bits: Bits

    calc_1: Calc
    calc_2: Calc

    clocks: Clocks

    counter_1: Counter
    counter_2: Counter
    counter_3: Counter
    counter_4: Counter
    counter_5: Counter
    counter_6: Counter
    counter_7: Counter
    counter_8: Counter

    div_1: Div
    div_2: Div
    div_3: Div
    div_4: Div

    filter: Filter

    inenc_1: InEnc
    inenc_2: InEnc
    inenc_3: InEnc

    lut_1: Lut
    lut_2: Lut
    lut_3: Lut
    lut_4: Lut
    lut_5: Lut
    lut_6: Lut
    lut_7: Lut
    lut_8: Lut
