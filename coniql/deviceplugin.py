from typing import List, Dict, Any, TypeVar
from dataclasses import dataclass

from device.types.channel import ReadOnlyChannel

DEVICES: Dict[str, Any] = {}
CHANNELS: Dict[str, Any] = {}


DeviceAddress = List[str]


@dataclass
class ChannelAddress:
    device_address: DeviceAddress
    channel_name: str


T = TypeVar('T')
C = TypeVar('C', bound=ReadOnlyChannel)


def register_device(addr: DeviceAddress, device: T):
    DEVICES[addr] = device


def register_channel(addr: ChannelAddress, channel: C):
    CHANNELS[addr] = channel
