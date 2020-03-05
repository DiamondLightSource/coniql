from coniql._types import Channel
from coniql.devicelayer.environment import DeviceEnvironment
from device.channel.setup import setup
from device.pmac.control.trajectorycontrol import scan_points
from device.pmac.control.trajectorymodel import TrajectoryModel


class DeviceLayer:
    def __init__(self, env: DeviceEnvironment):
        self.env = env

    @classmethod
    def from_tree(cls, device_tree):
        return DeviceLayer(DeviceEnvironment(device_tree))

    def get_fields(self, resource_id: str):
        return self.env.get_fields(resource_id)

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
        stream = channel.monitor_readback()
        async for readback in stream:
            yield readback

    async def scan_points(self, pmac_id: str, model: TrajectoryModel):
        pmac = self.env.get_resource(pmac_id)
        await scan_points(pmac, model)
        return True

    # TODO: Device introspection

    async def startup(self):
        """Start any services the plugin needs. Don't block"""
        await setup(self.env.device_tree)

    async def shutdown(self):
        """Destroy the plugin and any connections it has"""
