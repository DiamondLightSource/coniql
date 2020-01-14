from dataclasses import dataclass

from coniql.util import doc_field
from device.devicetypes.channel import ReadOnlyChannel, ReadWriteChannel


@dataclass
class Joggable:
    """Device that allows manual jogging of some value"""
    jog_positive: ReadWriteChannel[bool] = doc_field(
        "Jogs +step_length if set to true")
    jog_negative: ReadWriteChannel[bool] = doc_field(
        "Jogs -step_length if set to true")
    step_length: ReadWriteChannel[float] = doc_field(
        "The length of a single jog")
