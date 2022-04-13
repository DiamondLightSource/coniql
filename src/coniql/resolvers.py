import asyncio
import base64
import datetime
import json
from fnmatch import fnmatch
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

import numpy as np
from tartiflette import Resolver, Subscription

from coniql.coniql_schema import DisplayForm
from coniql.device_config import ChannelConfig, Child, DeviceInstance, Group, walk
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


@Resolver("Query.getChannel")
async def get_channel(parent, args: Dict[str, Any], ctx, info) -> DeferredChannel:
    return GetChannel(args["id"], args["timeout"], ctx["store"])


@Resolver("Query.getChannels")
async def get_channels(
    parent, args: Dict[str, Any], ctx, info
) -> Sequence[DeferredChannel]:
    store: PluginStore = ctx["store"]
    channels = []
    for channel_id in store.channels:
        if fnmatch(channel_id, args["filter"]):
            channels.append(GetChannel(channel_id, args["timeout"], store))
    return channels


@Resolver("Query.getChannelConfig")
async def get_channel_config(parent, args: Dict[str, Any], ctx, info) -> ChannelConfig:
    store: PluginStore = ctx["store"]
    channel_config = store.plugin_config_id(args["id"])[1]
    return channel_config


@Resolver("Query.getDevice")
async def get_device(parent, args: Dict[str, Any], ctx, info) -> Dict[str, Any]:
    store: PluginStore = ctx["store"]
    device_config = store.devices[args["id"]]
    return dict(id=args["id"], children=device_config.children)


@Resolver("Query.getDevices")
async def get_devices(parent, args: Dict[str, Any], ctx, info) -> List[Dict[str, Any]]:
    store: PluginStore = ctx["store"]
    devices = []
    for device_id, device_config in store.devices.items():
        if fnmatch(device_id, args["filter"]):
            devices.append(dict(id=device_id, children=device_config.children))
    return devices


@Resolver("Mutation.putChannels")
async def put_channel(
    parent, args: Dict[str, Any], ctx, info
) -> Sequence[DeferredChannel]:
    store: PluginStore = ctx["store"]
    pvs = []
    plugins = set()
    for channel_id in args["ids"]:
        plugin, config, channel_id = store.plugin_config_id(channel_id)
        pv = config.write_pv
        assert pv, f"{channel_id} is configured read-only"
        plugins.add(plugin)
        pvs.append(store.transport_pv(pv)[1])
    values = []
    for value in args["values"]:
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
    await plugins.pop().put_channels(pvs, values, args["timeout"])
    channels = [
        GetChannel(channel_id, args["timeout"], store) for channel_id in args["ids"]
    ]
    return channels


@Subscription("Subscription.subscribeChannel")
async def subscribe_channel(
    parent, args: Dict[str, Any], ctx, info
) -> AsyncIterator[Dict[str, Any]]:
    store: PluginStore = ctx["store"]
    plugin, config, channel_id = store.plugin_config_id(args["id"])
    # Remove the transport prefix from the read pv
    pv = store.transport_pv(config.read_pv)[1]
    async for channel in plugin.subscribe_channel(pv, config):
        yield dict(subscribeChannel=SubscribeChannel(channel_id, channel))


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
        pv = parent.write_pv or parent.read_pv
        assert pv, f"No PV for {parent}"
        channel = GetChannel(pv, 5.0, ctx["store"])
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
