import dataclasses

from typing import List, Dict, Any, Optional

from coniql._types import Channel, Function, ChannelStatus, ChannelQuality, \
    Readback
from coniql.plugin import Plugin
from device.cothread.channel import ReadOnlyCaChannel, ReadWriteCaChannel
from device.devicetypes.channel import ReadWriteChannel
from device.inmemory.channel import InMemoryReadOnlyChannel, InMemoryReadWriteChannel
from device.devices.goniometer import Goniometer
from device.devices.motor import Motor
from device.devices.stage3d import Stage3D

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

    def lookup_channel(self, channel_addr: List[str], channels: Optional[Dict[str, Any]] = None) -> ReadWriteChannel:
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
        readback = await channel.get()
        return readback.to_gql_readback()

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


def mock_device_environment() -> DevicePlugin:
    def mock_motor(position: float = 0.0) -> Motor:
        return Motor(
            position=InMemoryReadOnlyChannel(position),
            setpoint=InMemoryReadWriteChannel(position),
            p=InMemoryReadWriteChannel(1.0),
            i=InMemoryReadWriteChannel(0.0),
            d=InMemoryReadWriteChannel(0.0),
            jog_positive=InMemoryReadWriteChannel(False),
            jog_negative=InMemoryReadWriteChannel(False),
            step_length=InMemoryReadWriteChannel(1.0),
            velocity=InMemoryReadWriteChannel(1.0),
            min=InMemoryReadWriteChannel(-1000.0),
            max=InMemoryReadWriteChannel(1000.0)
        )

    goniometer = Goniometer(
        omega=mock_motor(),
        chi=mock_motor(),
        phi=mock_motor(),
        sample=Stage3D(
            x=mock_motor(),
            y=mock_motor(),
            z=mock_motor()
        )
    )

    plugin = DevicePlugin()
    plugin.register_device(goniometer, name='goniometer')

    plugin.debug()
    return plugin


def adsim_device_environment():
    def motor(prefix: str) -> Motor:
        return Motor(
            position=ReadOnlyCaChannel(f'{prefix}.RBV'),
            setpoint=ReadWriteCaChannel(f'{prefix}'),
            stationary=ReadOnlyCaChannel(f'{prefix}.DMOV'),
            p=ReadWriteCaChannel(f'{prefix}.PCOF'),
            i=ReadWriteCaChannel(f'{prefix}.ICOF'),
            d=ReadWriteCaChannel(f'{prefix}.DCOF'),
            jog_positive=ReadWriteCaChannel(f'{prefix}.TWF'),
            jog_negative=ReadWriteCaChannel(f'{prefix}.TWR'),
            step_length=ReadWriteCaChannel(f'{prefix}.TWV'),
            velocity=ReadWriteCaChannel(f'{prefix}.VELO'),
            max_velocity=ReadWriteCaChannel(f'{prefix}.VMAX'),
            min=ReadWriteCaChannel(f'{prefix}.LLM'),
            max=ReadWriteCaChannel(f'{prefix}.HLM')
        )

    x = motor('ws415-MO-SIM-01:M1')
    y = motor('ws415-MO-SIM-01:M2')
    z = motor('ws415-MO-SIM-01:M3')

    plugin = DevicePlugin()
    plugin.register_device(x, name='x')
    plugin.register_device(y, name='y')
    plugin.register_device(z, name='z')

    plugin.debug()
    return plugin

