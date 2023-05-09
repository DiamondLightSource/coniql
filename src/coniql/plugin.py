from typing import AsyncIterator, Dict, List, Sequence, Tuple, Union

import numpy as np

from coniql.types import Channel

PutValue = Union[bool, int, float, str, List[str], np.ndarray]


class Plugin:
    transport: str

    async def get_channel(self, pv: str, timeout: float) -> Channel:
        """Get the current structure of a Channel"""
        raise NotImplementedError(self)

    async def put_channels(
        self, pvs: List[str], values: Sequence[PutValue], timeout: float
    ):
        """Put a value to a channel, returning the structure after put"""
        raise NotImplementedError(self)

    async def subscribe_channel(self, pv: str) -> AsyncIterator[Channel]:
        """Subscribe to the structure of the Channel, yielding structures
        where only changing top level fields are filled in"""
        raise NotImplementedError(self)
        yield


class PluginStore:
    def __init__(self) -> None:
        # {transport: plugin}
        self.plugins: Dict[str, Plugin] = {}

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

    def plugin_config_id(self, channel_id: str) -> Tuple[Plugin, str]:
        transport, pv = self.transport_pv(channel_id)
        channel_id = f"{transport}://{pv}"
        plugin = self.plugins[transport]
        return plugin, channel_id
