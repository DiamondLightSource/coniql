import dataclasses

from typing import List, Dict, Any, Optional

from coniql._types import Channel, Function
from coniql.plugin import Plugin
from device.channel.channeltypes.channel import ReadWriteChannel

ADDRESS_DELIMETER = '.'


def parse_channel_address(channel_id: str) -> List[str]:
    return channel_id.split(ADDRESS_DELIMETER)


class DevicePlugin(Plugin):
    def __init__(self):
        self.channels = {}

    def register_device(self, device: Any, name: Optional[str] = None):
        """Registers a device and its channels and subdevices with the plugin"""
        d = dataclasses.asdict(device)
        if name is not None:
            d = {name: d}
        self.channels = {**self.channels, **d}

    def lookup_channel(self, channel_addr: List[str], channels: Optional[
        Dict[str, Any]] = None) -> ReadWriteChannel:
        if channels is None:
            channels = self.channels
        nxt = channel_addr[0]
        if len(channel_addr) == 1:
            return channels[nxt]
        elif len(channel_addr) > 1:
            return self.lookup_channel(channel_addr[1:], channels[nxt])
        else:
            raise Exception('Eerrm')

    def debug(self):
        import pprint
        pprint.pprint(self.channels)

    async def read_channel(self, channel_id: str, timeout: float):
        channel = self.lookup_channel(parse_channel_address(channel_id))
        readback = await channel.get_readback()
        return readback

    async def get_channel(self, channel_id: str) -> Channel:
        """Get the current structure of a Channel"""
        channel = self.lookup_channel(parse_channel_address(channel_id))
        if channel is not None:
            return Channel(id=channel_id)
        else:
            raise KeyError(f'Unknown channel: {channel_id}')

    async def get_function(self, function_id: str, timeout: float) -> Function:
        """Get the current structure of a Function"""
        raise NotImplementedError(self)

    async def put_channel(self, channel_id: str, value, timeout: float
                          ) -> Channel:
        """Put a value to a channel, returning the value after put"""
        channel = self.lookup_channel(parse_channel_address(channel_id))
        result = await channel.put(value)
        return await self.get_channel(channel_id)

    async def call_function(self, function_id: str, arguments, timeout: float
                            ) -> Any:
        """Call a function and return the result"""
        raise NotImplementedError(self)

    async def subscribe_channel(self, channel_id: str):
        """Subscribe to the structure of the value, yielding dict structures
        where only changing top level fields are filled in"""
        channel = self.lookup_channel(parse_channel_address(channel_id))
        stream = channel.monitor()
        async for readback in stream:
            yield readback.to_gql_readback()

    def startup(self):
        """Start any services the plugin needs. Don't block"""

    def shutdown(self):
        """Destroy the plugin and any connections it has"""
