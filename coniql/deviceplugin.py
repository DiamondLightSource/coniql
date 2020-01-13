import dataclasses

from typing import List, Dict, Any, TypeVar, Optional
from dataclasses import dataclass

from coniql._types import Channel, Function, ChannelStatus, ChannelQuality
from coniql.plugin import Plugin
from device.types.channel import ReadOnlyChannel, ReadWriteChannel


class DevicePlugin(Plugin):
    def __init__(self):
        self.channels = {}

    def register_device(self, device: Any):
        """Registers a device and its channels and subdevices with the plugin"""
        d = dataclasses.asdict(device)
        self.channels = {**self.channels, **d}

    def lookup_channel(self, channel_id: str, channels: Optional[Dict[str, Any]] = None) -> ReadWriteChannel:
        if channels is None:
            channels = self.channels
        if channel_id in channels:
            return channels[channel_id]
        for k, v in channels.items():
            if isinstance(v, dict):
                return self.lookup_channel(channel_id, v)
        raise KeyError()

    async def get_channel(self, channel_id: str, timeout: float) -> Channel:
        """Get the current structure of a Channel"""
        channel = self.lookup_channel(channel_id)
        result = await channel.get_async()
        if result.is_present():
            return Channel(id=channel_id, value=result.or_raise(Exception()))
        else:
            return Channel(id=channel_id, status=ChannelStatus(quality=ChannelQuality.INVALID))

    async def get_function(self, function_id: str, timeout: float) -> Function:
        """Get the current structure of a Function"""
        raise NotImplementedError(self)

    async def put_channel(self, channel_id: str, value, timeout: float
                          ) -> Channel:
        """Put a value to a channel, returning the value after put"""
        channel = self.lookup_channel(channel_id)
        result = await channel.put_async(value)
        return await self.get_channel(channel_id, timeout)

    async def call_function(self, function_id: str, arguments, timeout: float
                            ) -> Any:
        """Call a function and return the result"""
        raise NotImplementedError(self)

    async def subscribe_channel(self, channel_id: str):
        """Subscribe to the structure of the value, yielding dict structures
        where only changing top level fields are filled in"""
        yield
        raise NotImplementedError(self)

    def startup(self):
        """Start any services the plugin needs. Don't block"""

    def shutdown(self):
        """Destroy the plugin and any connections it has"""


def mock_device_environment():
    goniometer = G