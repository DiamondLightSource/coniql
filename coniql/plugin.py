import os
from pathlib import Path
from typing import AsyncIterator, Dict, List, Tuple, Union

import numpy as np

from coniql.device_config import ChannelConfig, DeviceConfig, DeviceInstance, walk
from coniql.types import Channel

PutValue = Union[bool, int, float, str, List[str], np.ndarray]


class Plugin:
    transport: str

    async def get_channel(
        self, pv: str, timeout: float, config: ChannelConfig
    ) -> Channel:
        """Get the current structure of a Channel"""
        raise NotImplementedError(self)

    async def put_channels(
        self, pvs: List[str], values: List[PutValue], timeout: float
    ):
        """Put a value to a channel, returning the structure after put"""
        raise NotImplementedError(self)

    async def subscribe_channel(
        self, pv: str, config: ChannelConfig
    ) -> AsyncIterator[Channel]:
        """Subscribe to the structure of the Channel, yielding structures
        where only changing top level fields are filled in"""
        raise NotImplementedError(self)
        yield


class PluginStore:
    def __init__(self):
        # {transport: plugin}
        self.plugins: Dict[str, Plugin] = {}
        # {device_id: device_config}
        self.devices: Dict[str, DeviceConfig] = {}
        # {fully_qualified_channel_id: channel_config}
        self.channels: Dict[str, ChannelConfig] = {}

    def add_plugin(self, transport: str, plugin: Plugin, set_default=False):
        self.plugins[transport] = plugin
        plugin.transport = transport
        if set_default:
            self.plugins[""] = plugin

    def transport_pv(self, channel_id: str) -> Tuple[str, str]:
        """Take a channel_id with an optional transport prefix and
        return the transport and pv components"""
        split = channel_id.split("://", 1)
        if len(split) == 1:
            transport, pv = self.plugins[""].transport, channel_id
        else:
            transport, pv = split
        return transport, pv

    def add_device_config(self, path: Path, device_id="", macros=None):
        """Load a top level .coniql.yaml file with devices in it"""
        device_config = DeviceConfig.from_yaml(path, macros)
        if device_id:
            self.devices[device_id] = device_config
        # Relative paths are relative to the path being loaded, so go there
        cwd = Path.cwd()
        os.chdir(path.resolve().parent)
        try:
            for child in walk(device_config.children):
                if isinstance(child, ChannelConfig):
                    # TODO: selectively update channel if already exists
                    transport, pv = self.transport_pv(child.write_pv or child.read_pv)
                    self.channels[f"{transport}://{pv}"] = child
                elif isinstance(child, DeviceInstance):
                    # recursively load child devices
                    if child.id is None:
                        if device_id:
                            child.id = device_id + "." + child.name
                        else:
                            child.id = child.name
                    self.add_device_config(child.file, child.id, child.macros)
        finally:
            os.chdir(cwd)
        return device_config

    def plugin_config_id(self, channel_id: str) -> Tuple[Plugin, ChannelConfig, str]:
        transport, pv = self.transport_pv(channel_id)
        channel_id = f"{transport}://{pv}"
        plugin = self.plugins[transport]
        config = self.channels.get(channel_id, None)
        if config is None:
            # None exists, make a RW config
            config = ChannelConfig(name="", read_pv=channel_id, write_pv=channel_id)
        return plugin, config, channel_id
