import asyncio
import base64
import datetime
import json
from fnmatch import fnmatch
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

import numpy as np
from tartiflette import Resolver, Subscription

from coniql.coniql_schema import DisplayForm
from coniql.device_config import (
    ChannelConfig,
    Child,
    ConfigStore,
    DeviceInstance,
    Group,
    walk,
)
from coniql.plugin import PluginStore
from coniql.types import (
    Channel,
    ChannelDisplay,
    ChannelStatus,
    ChannelTime,
    ChannelValue,
)


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
    def __init__(self, id: str, timeout: float, ctx):
        plugins: PluginStore = ctx["plugins"]
        configs: ConfigStore = ctx["configs"]
        self.config = configs.channels.get(id, NO_CONFIG)
        self.timeout = timeout
        self.plugin, self.channel_id = plugins.plugin_channel_id(id)
        self.id = self.plugin.full_id(self.channel_id)
        self.lock = asyncio.Lock()

    async def populate_channel(self) -> Channel:
        channel = await self.plugin.get_channel(
            self.channel_id, self.timeout, self.config
        )
        return channel


class ResolvedChannel(DeferredChannel):
    def __init__(self, id: str, channel: Channel):
        self.id = id
        self.channel = channel


@Resolver("Query.getChannel")
async def get_channel(parent, args: Dict[str, Any], ctx, info) -> DeferredChannel:
    return GetChannel(args["id"], args["timeout"], ctx)


@Resolver("Query.getChannels")
async def get_channels(
    parent, args: Dict[str, Any], ctx, info
) -> Sequence[DeferredChannel]:
    configs: ConfigStore = ctx["configs"]
    channels = []
    for channel_id in configs.channels:
        if fnmatch(channel_id, args["filter"]):
            channels.append(GetChannel(channel_id, args["timeout"], ctx))
    return channels


@Resolver("Query.getChannelConfig")
async def get_channel_config(parent, args: Dict[str, Any], ctx, info) -> ChannelConfig:
    configs: ConfigStore = ctx["configs"]
    channel_config = configs.channels[args["id"]]
    return channel_config


@Resolver("Query.getDevice")
async def get_device(parent, args: Dict[str, Any], ctx, info) -> Dict[str, Any]:
    configs: ConfigStore = ctx["configs"]
    device_config = configs.devices[args["id"]]
    return dict(id=args["id"], children=device_config.children)


@Resolver("Query.getDevices")
async def get_devices(parent, args: Dict[str, Any], ctx, info) -> List[Dict[str, Any]]:
    configs: ConfigStore = ctx["configs"]
    devices = []
    for device_id, device_config in configs.devices.items():
        if fnmatch(device_id, args["filter"]):
            devices.append(dict(id=device_id, children=device_config.children))
    return devices


@Resolver("Mutation.putChannel")
async def put_channel(parent, args: Dict[str, Any], ctx, info) -> DeferredChannel:
    plugins: PluginStore = ctx["plugins"]
    configs: ConfigStore = ctx["configs"]
    plugin, channel_id = plugins.plugin_channel_id(args["id"])
    config = configs.channels.get(args["id"], NO_CONFIG)
    value = args["value"]
    if value[:1] in "[{":
        # need to json decode
        value = json.loads(value)
        if isinstance(value, dict):
            # decode base64 array
            dtype = np.dtype(value["numberType"].lower())
            value_b = base64.b64decode(value["base64"])
            # https://stackoverflow.com/a/6485943
            value = np.frombuffer(value_b, dtype=dtype)
    channel = ResolvedChannel(
        id=plugin.full_id(channel_id),
        channel=await plugin.put_channel(channel_id, value, args["timeout"], config),
    )
    return channel


@Subscription("Subscription.subscribeChannel")
async def subscribe_channel(
    parent, args: Dict[str, Any], ctx, info
) -> AsyncIterator[Dict[str, Any]]:
    plugins: PluginStore = ctx["plugins"]
    configs: ConfigStore = ctx["configs"]
    plugin, channel_id = plugins.plugin_channel_id(args["id"])
    full_id = plugin.full_id(channel_id)
    config = configs.channels.get(args["id"], NO_CONFIG)
    async for channel in plugin.subscribe_channel(channel_id, config):
        yield dict(subscribeChannel=ResolvedChannel(full_id, channel))


@Resolver("Device.children")
async def device_children(parent: Dict[str, Any], args, ctx, info) -> List:
    children = parent["children"]
    if args["flatten"]:
        children = list(walk(children))
    return children


@Resolver("NamedChild.label")
async def named_child_label(parent: Child, args, ctx, info) -> str:
    return parent.get_label()


def child_type_resolver(result, ctx, info, abstract_type):
    if isinstance(result, Group):
        return "Group"
    elif isinstance(result, DeferredChannel):
        return "Channel"
    else:
        return "Device"


@Resolver("NamedChild.child", type_resolver=child_type_resolver)
async def named_child_child(parent: Child, args, ctx, info):
    if isinstance(parent, ChannelConfig):
        # TODO: pass tImeout down
        channel = GetChannel(parent.write_pv or parent.read_pv, 5.0, ctx)
        return channel
    elif isinstance(parent, DeviceInstance):
        device = await get_device(parent, dict(id=parent.id), ctx, info)
        return device
    else:
        return parent


@Resolver("ChannelConfig.readPv")
async def channel_config_read_pv(parent: ChannelConfig, args, ctx, info) -> str:
    return parent.read_pv


@Resolver("ChannelConfig.writePv")
async def channel_config_write_pv(parent: ChannelConfig, args, ctx, info) -> str:
    return parent.write_pv


@Resolver("ChannelConfig.displayForm")
async def channel_config_display_form(
    parent: ChannelConfig, args, ctx, info
) -> DisplayForm:
    return parent.display_form


@Resolver("Channel.value")
async def channel_value(
    parent: DeferredChannel, args, ctx, info
) -> Optional[ChannelValue]:
    channel = await parent.get_channel()
    return channel.get_value()


@Resolver("Channel.status")
async def channel_status(
    parent: DeferredChannel, args, ctx, info
) -> Optional[ChannelStatus]:
    channel = await parent.get_channel()
    return channel.get_status()


@Resolver("Channel.display")
async def channel_display(
    parent: DeferredChannel, args, ctx, info
) -> Optional[ChannelDisplay]:
    channel = await parent.get_channel()
    return channel.get_display()


@Resolver("Channel.time")
async def channel_time(
    parent: DeferredChannel, args, ctx, info
) -> Optional[ChannelTime]:
    channel = await parent.get_channel()
    return channel.get_time()


@Resolver("ChannelTime.datetime")
async def channel_time_datetime(
    parent: ChannelTime, args, ctx, info
) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(parent.seconds)


@Resolver("ChannelValue.string")
async def channel_value_string(parent: ChannelValue, args, ctx, info) -> str:
    if args["units"]:
        return parent.formatter.to_string_with_units(parent.value)
    else:
        return parent.formatter.to_string(parent.value)


@Resolver("ChannelValue.float")
async def channel_value_float(parent: ChannelValue, args, ctx, info) -> Optional[float]:
    return parent.formatter.to_float(parent.value)


@Resolver("ChannelValue.base64Array")
async def channel_value_base64_array(
    parent: ChannelValue, args, ctx, info
) -> Optional[Dict[str, str]]:
    return parent.formatter.to_base64_array(parent.value, args["length"])


@Resolver("ChannelValue.stringArray")
async def channel_value_string_array(
    parent: ChannelValue, args, ctx, info
) -> Optional[List[str]]:
    return parent.formatter.to_string_array(parent.value, args["length"])
