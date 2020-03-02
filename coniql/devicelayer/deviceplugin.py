from coniql._types import Channel
from coniql.devicelayer.environment import DeviceEnvironment


class DeviceLayer:
    def __init__(self, env: DeviceEnvironment):
        self.env = env

    @classmethod
    def from_tree(cls, device_tree):
        return DeviceLayer(DeviceEnvironment(device_tree))

    async def read_channel(self, channel_id: str):
        channel = self.env.get_resource(channel_id)
        readback = await channel.get_readback()
        return readback

    async def get_channel(self, channel_id: str) -> Channel:
        """Get the current structure of a Channel"""
        channel = self.env.get_resource(channel_id)
        return Channel(id=channel_id)

    async def put_channel(self, channel_id: str, value) -> bool:
        """Put a value to a channel, returning the value after put"""
        channel = self.env.get_resource(channel_id)
        return await channel.put(value)

    async def subscribe_channel(self, channel_id: str):
        """Subscribe to the structure of the value, yielding dict structures
        where only changing top level fields are filled in"""
        channel = self.env.get_resource(channel_id)
        stream = channel.monitor()
        async for readback in stream:
            yield readback

    # TODO: Device introspection

    def startup(self):
        """Start any services the plugin needs. Don't block"""

    def shutdown(self):
        """Destroy the plugin and any connections it has"""
