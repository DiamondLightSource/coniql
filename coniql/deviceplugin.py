import dataclasses

from typing import List, Dict, Any, Optional

from coniql._types import Channel, Function, ChannelStatus, ChannelQuality, \
    Readback
from coniql.plugin import Plugin
from device.cothread.cabool import CaBool
from device.cothread.caenum import CaEnum
from device.cothread.channel import CaChannel
from device.devices.faketriggerbox import in_memory_box_running, FakeTriggerBox
from device.devicetypes.channel import ReadWriteChannel
from device.inmemory.channel import InMemoryReadOnlyChannel, \
    InMemoryReadWriteChannel
from device.devices.goniometer import Goniometer
from device.devices.motor import Motor
from device.devices.stage3d import Stage3D
from device.devices.camera import Camera

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


@dataclasses.dataclass
class AdSimBeamline:
    trigger_box: FakeTriggerBox
    detector: Camera
    stage: Stage3D


def adsim_device_environment():
    beamline = adsim_environment()

    plugin = DevicePlugin()
    plugin.register_device(beamline, name='beamline')

    plugin.debug()
    return plugin


def adsim_environment():
    def motor(prefix: str) -> Motor:
        return Motor(
            position=CaChannel(f'{prefix}.RBV'),
            setpoint=CaChannel(f'{prefix}'),
            stationary=CaChannel(f'{prefix}.DMOV'),
            p=CaChannel(f'{prefix}.PCOF'),
            i=CaChannel(f'{prefix}.ICOF'),
            d=CaChannel(f'{prefix}.DCOF'),
            jog_positive=CaBool(f'{prefix}.TWF'),
            jog_negative=CaBool(f'{prefix}.TWR'),
            step_length=CaChannel(f'{prefix}.TWV'),
            velocity=CaChannel(f'{prefix}.VELO'),
            max_velocity=CaChannel(f'{prefix}.VMAX'),
            min=CaChannel(f'{prefix}.LLM'),
            max=CaChannel(f'{prefix}.HLM')
        )

    def camera(prefix: str) -> Camera:
        return Camera(
            exposure_time=CaChannel(f'{prefix}:AcquireTime',
                                             rbv_suffix='_RBV'),
            acquire_period=CaChannel(f'{prefix}:AcquirePeriod',
                                              rbv_suffix='_RBV'),
            exposures_per_image=CaChannel(f'{prefix}:NumExposures',
                                                   rbv_suffix='_RBV'),
            number_of_images=CaChannel(f'{prefix}:NumImages',
                                                rbv_suffix='_RBV'),
            image_mode=CaEnum(f'{prefix}:ImageMode',
                                          rbv_suffix='_RBV'),
            trigger_mode=CaEnum(f'{prefix}:TriggerMode',
                                            rbv_suffix='_RBV'),
            acquire=CaBool(f'{prefix}:Acquire'),
            array_counter=CaChannel(f'{prefix}:ArrayCounter',
                                             rbv_suffix='_RBV'),
            framerate=CaChannel(f'{prefix}:ArrayRate_RBV')
        )

    x = motor('ws415-MO-SIM-01:M1')
    y = motor('ws415-MO-SIM-01:M2')
    z = motor('ws415-MO-SIM-01:M3')
    sample_stage = Stage3D(x, y, z)
    det = camera('ws415-AD-SIM-01:CAM')
    trigger_box = in_memory_box_running()
    beamline = AdSimBeamline(
        trigger_box=trigger_box,
        detector=det,
        stage=sample_stage
    )
    return beamline
