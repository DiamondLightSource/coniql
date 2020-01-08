from typing import List
from dataclasses import dataclass

DeviceAddress = List[str]


@dataclass
class ChannelAddress:
    device_address: DeviceAddress
    channel_name: str

