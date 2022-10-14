import asyncio
import base64
import datetime
import json
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

import numpy as np

from coniql.coniql_schema import DisplayForm
from coniql.device_config import ChannelConfig, Child, DeviceInstance, Group
from coniql.plugin import PluginStore
from coniql.types import (
    Channel,
    ChannelDisplay,
    ChannelStatus,
    ChannelTime,
    ChannelValue,
)


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class DeferredChannel:
    id: str
    lock: asyncio.Lock
    channel: Optional[Channel] = None

    async def populate_channel(self) -> Channel:
        raise NotImplementedError(self)

    async def get_channel(self) -> Channel:
        if self.channel is None:
            async with self.lock:
                # If channel is still None we should make it
                if self.channel is None:
                    self.channel = await self.populate_channel()
        assert self.channel
        return self.channel


NO_CONFIG = ChannelConfig(name="")


class GetChannel(DeferredChannel):
    def __init__(self, channel_id: str, timeout: float, store: PluginStore):
        self.plugin, self.config, self.id = store.plugin_config_id(channel_id)
        # Remove the transport prefix from the read pv
        self.pv = store.transport_pv(self.config.read_pv or self.config.write_pv)[1]
        self.timeout = timeout
        self.lock = asyncio.Lock()

    async def populate_channel(self) -> Channel:
        channel = await self.plugin.get_channel(self.pv, self.timeout, self.config)
        return channel


class SubscribeChannel(DeferredChannel):
    def __init__(self, channel_id: str, channel: Channel):
        self.id = channel_id
        self.channel = channel


async def get_channel(id, timeout, ctx) -> DeferredChannel:
    return GetChannel(id, timeout, ctx["store"])


# @Resolver("Query.getChannelConfig")
async def get_channel_config(parent, args: Dict[str, Any], ctx, info) -> ChannelConfig:
    store: PluginStore = ctx["store"]
    channel_config = store.plugin_config_id(args["id"])[1]
    return channel_config


# @Resolver("Query.getDevice")
async def get_device(parent, args: Dict[str, Any], ctx, info) -> Dict[str, Any]:
    store: PluginStore = ctx["store"]
    device_config = store.devices[args["id"]]
    return dict(id=args["id"], children=device_config.children)


async def put_channel(
    ids: List[str], put_values: List[str], timeout, ctx
) -> Sequence[DeferredChannel]:
    store: PluginStore = ctx["store"]
    pvs = []
    plugins = set()
    for channel_id in ids:
        plugin, config, channel_id = store.plugin_config_id(channel_id)
        pv = config.write_pv
        assert pv, f"{channel_id} is configured read-only"
        plugins.add(plugin)
        pvs.append(store.transport_pv(pv)[1])
    values = []
    for value in put_values:
        if value[:1] in "[{":
            # need to json decode
            value = json.loads(value)
            if isinstance(value, dict):
                # decode base64 array
                dtype = np.dtype(value["numberType"].lower())
                value_b = base64.b64decode(value["base64"])
                # https://stackoverflow.com/a/6485943
                value = np.frombuffer(value_b, dtype=dtype)
        values.append(value)
    assert len(values) == len(pvs), "Mismatch in ids and values length"
    assert len(plugins) == 1, "Can only put to pvs with the same transport, not %s" % [
        p.transport for p in plugins
    ]
    await plugins.pop().put_channels(pvs, values, timeout)
    channels = [GetChannel(channel_id, timeout, store) for channel_id in ids]
    return channels


async def subscribe_channel(id, ctx) -> AsyncIterator[Dict[str, Any]]:
    store: PluginStore = ctx["store"]
    plugin, config, channel_id = store.plugin_config_id(id)
    # Remove the transport prefix from the read pv
    pv = store.transport_pv(config.read_pv)[1]
    async for channel in plugin.subscribe_channel(pv, config):
        yield SubscribeChannel(channel_id, channel)
        # yield dict(subscribeChannel=SubscribeChannel(channel_id, channel))


# @Resolver("NamedChild.label")
async def named_child_label(parent: Child, args, ctx, info) -> str:
    return parent.get_label()


def child_type_resolver(result, ctx, info, abstract_type):
    if isinstance(result, Group):
        return "Group"
    elif isinstance(result, DeferredChannel):
        return "Channel"
    else:
        return "Device"


# @Resolver("NamedChild.child", type_resolver=child_type_resolver)
async def named_child_child(parent: Child, args, ctx, info):
    if isinstance(parent, ChannelConfig):
        # TODO: pass tImeout down
        pv = parent.write_pv or parent.read_pv
        assert pv, f"No PV for {parent}"
        channel = GetChannel(pv, 5.0, ctx["store"])
        return channel
    elif isinstance(parent, DeviceInstance):
        device = await get_device(parent, dict(id=parent.id), ctx, info)
        return device
    else:
        return parent


# @Resolver("ChannelConfig.readPv")
async def channel_config_read_pv(parent: ChannelConfig, args, ctx, info) -> str:
    return parent.read_pv


# @Resolver("ChannelConfig.writePv")
async def channel_config_write_pv(parent: ChannelConfig, args, ctx, info) -> str:
    return parent.write_pv


# @Resolver("ChannelConfig.displayForm")
async def channel_config_display_form(
    parent: ChannelConfig, args, ctx, info
) -> DisplayForm:
    return parent.display_form


async def channel_value(parent: DeferredChannel) -> Optional[ChannelValue]:
    channel = await parent.get_channel()
    return channel.get_value()


async def channel_status(parent: DeferredChannel) -> Optional[ChannelStatus]:
    channel = await parent.get_channel()
    return channel.get_status()


async def channel_display(parent: DeferredChannel) -> Optional[ChannelDisplay]:
    channel = await parent.get_channel()
    return channel.get_display()


async def channel_time(parent: DeferredChannel) -> Optional[ChannelTime]:
    channel = await parent.get_channel()
    return channel.get_time()


async def channel_time_datetime(parent: ChannelTime) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(parent.seconds)


async def channel_value_string(parent: ChannelValue, units) -> str:
    if units:
        return parent.formatter.to_string_with_units(parent.value)
    else:
        return parent.formatter.to_string(parent.value)


async def channel_value_float(parent: ChannelValue) -> Optional[float]:
    return parent.formatter.to_float(parent.value)


async def channel_value_base64_array(
    parent: ChannelValue, length: int
) -> Optional[Dict[str, str]]:
    res = parent.formatter.to_base64_array(parent.value, length)
    if res is not None:
        return dotdict(parent.formatter.to_base64_array(parent.value, length))
    else:
        return None


async def channel_value_string_array(
    parent: ChannelValue, length: int
) -> Optional[List[str]]:
    return parent.formatter.to_string_array(parent.value, length)