import numpy as np

from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadOnlyChannel
from device.adcore.plugin import AdPlugin


@dataclass
class ArrayPlugin(AdPlugin):
    array_data: ReadOnlyChannel[np.ndarray]
