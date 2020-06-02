import asyncio
import datetime
from fnmatch import fnmatch
from typing import Any, AsyncIterator, Dict, List, Optional

from tartiflette import Resolver, Subscription

from coniql.coniql_schema import DisplayForm
from coniql.device_config import ChannelConfig, ConfigStore
from coniql.plugin import PluginStore
from coniql.types import Channel, ChannelTime, ChannelValue


@Resolver("Query.getChannel")
async def get_channel(parent, args: Dict[str, Any], ctx, info) -> Channel:
    plugins: PluginStore = ctx["plugins"]
    configs: ConfigStore = ctx["configs"]
    plugin, channel_id = plugins.plugin_channel_id(args["id"])
    channel = await plugin.get_channel(channel_id, args["timeout"])
    configs.update_channel(channel)
    return channel


@Resolver("Query.getChannels")
async def get_channels(parent, args: Dict[str, Any], ctx, info) -> List[Channel]:
    configs: ConfigStore = ctx["configs"]
    coros = []
    for channel_id in configs.channels:
        if fnmatch(channel_id, args["filter"]):
            coros.append(
                get_channel(
                    parent, dict(id=channel_id, timeout=args["timeout"]), ctx, info
                )
            )
    channels = list(await asyncio.gather(*coros))
    return channels


@Resolver("Mutation.putChannel")
async def put_channel(parent, args: Dict[str, Any], ctx, info) -> Channel:
    plugins: PluginStore = ctx["plugins"]
    configs: ConfigStore = ctx["configs"]
    plugin, channel_id = plugins.plugin_channel_id(args["id"])
    channel = await plugin.put_channel(channel_id, args["value"], args["timeout"])
    configs.update_channel(channel)
    return channel


@Subscription("Subscription.subscribeChannel")
async def subscribe_channel(
    parent, args: Dict[str, Any], ctx, info
) -> AsyncIterator[Dict[str, Channel]]:
    plugins: PluginStore = ctx["plugins"]
    configs: ConfigStore = ctx["configs"]
    plugin, channel_id = plugins.plugin_channel_id(args["id"])
    async for channel in plugin.subscribe_channel(channel_id):
        yield dict(subscribeChannel=configs.update_channel(channel))


@Resolver("Query.getChannelConfig")
async def get_channel_config(parent, args: Dict[str, Any], ctx, info) -> ChannelConfig:
    configs: ConfigStore = ctx["configs"]
    channel_config = configs.channels[args["id"]]
    return channel_config


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
