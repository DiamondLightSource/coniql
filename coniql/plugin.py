from typing import AsyncIterator, Dict, Tuple

from coniql.types import Channel


class Plugin:
    name: str

    async def get_channel(self, channel_id: str, timeout: float) -> Channel:
        """Get the current structure of a Channel"""
        raise NotImplementedError(self)

    async def put_channel(self, channel_id: str, value, timeout: float) -> Channel:
        """Put a value to a channel, returning the value after put"""
        raise NotImplementedError(self)

    async def subscribe_channel(self, channel_id: str) -> AsyncIterator[Channel]:
        """Subscribe to the structure of the value, yielding dict structures
        where only changing top level fields are filled in"""
        raise NotImplementedError(self)
        yield


class PluginStore:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}

    def add_plugin(self, name: str, plugin: Plugin, set_default=False):
        self.plugins[name] = plugin
        plugin.name = name
        if set_default:
            self.plugins[""] = plugin

    def plugin_channel_id(self, id: str) -> Tuple[Plugin, str]:
        split = id.split("://", 1)
        if len(split) == 1:
            scheme, channel_id = "", id
        else:
            scheme, channel_id = split
        try:
            plugin = self.plugins[scheme]
        except KeyError:
            raise ValueError("No plugin registered for scheme '%s'" % scheme)
        return plugin, channel_id
