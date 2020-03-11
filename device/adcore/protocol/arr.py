import numpy as np

from typing_extensions import Protocol

from device.channel.channeltypes.channel import ReadOnlyChannel
from device.adcore.protocol.plugin import AdPlugin


class ArrayPlugin(AdPlugin, Protocol):
    array_data: ReadOnlyChannel[np.ndarray]
