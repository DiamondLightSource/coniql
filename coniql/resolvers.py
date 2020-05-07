import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from tartiflette import Resolver, Subscription

from coniql.types import ChannelTime, ChannelValue


@Resolver("Query.getChannel")
async def get_channel(parent, args: Dict[str, Any], ctx, info) -> Dict[str, Any]:
    plugin, channel_id = ctx["plugins"].plugin_channel_id(args["id"])
    data = await plugin.get_channel(channel_id, args["timeout"])
    return data


@Resolver("Mutation.putChannel")
async def put_channel(parent, args: Dict[str, Any], ctx, info) -> Dict[str, Any]:
    plugin, channel_id = ctx["plugins"].plugin_channel_id(args["id"])
    data = await plugin.put_channel(channel_id, args["value"], args["timeout"])
    return data


@Subscription("Subscription.subscribeChannel")
async def subscribe_channel(
    parent, args: Dict[str, Any], ctx, info
) -> AsyncIterator[Dict[str, Any]]:
    plugin, channel_id = ctx["plugins"].plugin_channel_id(args["id"])
    async for data in plugin.subscribe_channel(channel_id):
        yield dict(subscribeChannel=data)


@Resolver("ChannelTime.datetime")
async def resolve_query_time(parent: ChannelTime, args, ctx, info) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(parent.seconds)


@Resolver("ChannelValue.string")
async def resolve_value_string(parent: ChannelValue, args, ctx, info) -> str:
    if args["units"]:
        return parent.formatter.to_string_with_units(parent.value)
    else:
        return parent.formatter.to_string(parent.value)


@Resolver("ChannelValue.float")
async def resolve_value_float(parent: ChannelValue, args, ctx, info) -> Optional[float]:
    return parent.formatter.to_float(parent.value)


@Resolver("ChannelValue.base64Array")
async def resolve_value_base64_array(
    parent: ChannelValue, args, ctx, info
) -> Optional[Dict[str, str]]:
    return parent.formatter.to_base64_array(parent.value, args["length"])


@Resolver("ChannelValue.stringArray")
async def resolve_value_string_array(
    parent: ChannelValue, args, ctx, info
) -> Optional[List[str]]:
    return parent.formatter.to_string_array(parent.value, args["length"])
