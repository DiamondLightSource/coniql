import asyncio
import base64
import datetime
import json
from enum import Enum
from typing import AsyncGenerator, List, Optional, Sequence, Union

import numpy as np
import strawberry

from coniql.caplugin import CAPlugin
from coniql.plugin import PluginStore
from coniql.simplugin import SimPlugin
from coniql.types import Base64Array as TypeBase64Array
from coniql.types import Channel as TypeChannel
from coniql.types import ChannelDisplay
from coniql.types import ChannelStatus as TypeChannelStatus
from coniql.types import ChannelTime as TypeChannelTime
from coniql.types import ChannelValue as TypeChannelValue

store_global = PluginStore()
store_global.add_plugin("ssim", SimPlugin())
store_global.add_plugin("ca", CAPlugin(), set_default=True)


class DeferredChannel(TypeChannel):
    id: str
    lock: asyncio.Lock
    channel: Optional[TypeChannel] = None

    async def populate_channel(self) -> TypeChannel:
        raise NotImplementedError(self)

    async def get_channel(self) -> TypeChannel:
        if self.channel is None:
            async with self.lock:
                # If channel is still None we should make it
                if self.channel is None:
                    self.channel = await self.populate_channel()
        assert self.channel
        return self.channel


class GetChannel(DeferredChannel):
    def __init__(self, channel_id: str, timeout: float, store: PluginStore):
        self.plugin, self.id = store.plugin_config_id(channel_id)
        # Remove the transport prefix from the read pv
        self.pv = store.transport_pv(channel_id)[1]
        self.timeout = timeout
        self.lock = asyncio.Lock()

    async def populate_channel(self) -> TypeChannel:
        channel = await self.plugin.get_channel(self.pv, self.timeout)
        return channel


class SubscribeChannel(DeferredChannel):
    def __init__(self, channel_id: str, channel: TypeChannel):
        self.id = channel_id
        self.channel = channel


@strawberry.enum
class ChannelQuality(Enum):
    """
    Indication of how the current value of a Channel should be interpreted
    """

    # Value is known, valid, nothing is wrong
    VALID = "VALID"
    # Value is known, valid, but is in the range generating a warning
    WARNING = "WARNING"
    # Value is known, valid, but is in the range generating an alarm condition
    ALARM = "ALARM"
    # Value is known, but not valid, e.g. a RW before its first put
    INVALID = "INVALID"
    # The value is unknown, for instance because the channel is disconnected
    UNDEFINED = "UNDEFINED"
    # The Channel is currently in the process of being changed
    CHANGING = "CHANGING"


async def resolve_float(root: TypeChannelValue) -> Optional[float]:
    return root.formatter.to_float(root.value)


async def resolve_string(root: TypeChannelValue, units: bool = False) -> Optional[str]:
    if units:
        return root.formatter.to_string_with_units(root.value)
    else:
        return root.formatter.to_string(root.value)


async def resolve_base64Array(
    root: TypeChannelValue, length: int = 0
) -> Optional[TypeBase64Array]:
    return root.formatter.to_base64_array(root.value, length)


async def resolve_stringArray(
    root: TypeChannelValue, length: int = 0
) -> Optional[List[str]]:
    return root.formatter.to_string_array(root.value, length)


@strawberry.type
class ChannelValue:
    """
    Value that can be formatted in a number of ways
    """

    # The current value formatted as a Float, Null if not expressable
    float = strawberry.field(resolver=resolve_float)
    # The current value formatted as a string
    string = strawberry.field(resolver=resolve_string)
    # Array of base64 encoded numbers, Null if not expressable
    base64Array = strawberry.field(resolver=resolve_base64Array)
    # Array of strings, Null if not expressable
    stringArray = strawberry.field(resolver=resolve_stringArray)


@strawberry.type
class ChannelStatus(TypeChannelStatus):
    """
    The current status of a Channel, including alarm and connection status.
    Inherit directly from TypeChannelStatus.
    """

    pass


def resolver_datetime(root: TypeChannelTime) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(root.seconds)


@strawberry.type
class ChannelTime(TypeChannelTime):
    """
    Timestamp indicating when a value was last updated.
    Inherit fields from TypeChannelTime.
    """

    @strawberry.field
    async def datetime(root: TypeChannelTime) -> datetime.datetime:
        """The timestamp as a datetime object"""
        return datetime.datetime.fromtimestamp(root.seconds)


async def resolver_value(root: DeferredChannel) -> Optional[TypeChannelValue]:
    channel = await root.get_channel()
    return channel.get_value()


async def resolver_time(root: DeferredChannel) -> Optional[TypeChannelTime]:
    channel = await root.get_channel()
    return channel.get_time()


async def resolver_status(root: DeferredChannel) -> Optional[TypeChannelStatus]:
    channel = await root.get_channel()
    return channel.get_status()


async def resolver_display(root: DeferredChannel) -> Optional[ChannelDisplay]:
    channel = await root.get_channel()
    return channel.get_display()


@strawberry.type
class Channel:
    """
    A single value with associated time, status and metadata. These values
    can be Null so that in a subscription they are only updated on change
    """

    # ID that uniquely defines this Channel, normally a PV
    id: strawberry.ID
    # The current value of this channel
    value: Optional[ChannelValue] = strawberry.field(resolver=resolver_value)
    # When was the value last updated
    time: Optional[ChannelTime] = strawberry.field(resolver=resolver_time)
    # Status of the connection, whether is is mutable, and alarm info
    status: Optional[ChannelStatus] = strawberry.field(resolver=resolver_status)
    # How should the Channel be displayed
    display: Optional[ChannelDisplay] = strawberry.field(resolver=resolver_display)


def get_channel(id: strawberry.ID, timeout: float = 5.0) -> TypeChannel:
    return GetChannel(id, timeout, store_global)


@strawberry.type
class Query:
    # Get the current value of a Channel
    getChannel: Channel = strawberry.field(resolver=get_channel)


async def subscribe_channel(id: strawberry.ID) -> AsyncGenerator[TypeChannel, None]:
    """Subscribe to changes in top level fields of Channel,
    if they haven't changed they will be Null"""
    store: PluginStore = store_global
    plugin, channel_id = store.plugin_config_id(id)
    # Remove the transport prefix from the read pv
    pv = store.transport_pv(id)[1]
    async for channel in plugin.subscribe_channel(pv):
        yield SubscribeChannel(channel_id, channel)


@strawberry.type
class Subscription:
    """Tell mypy to ignore this line as it complains 'expression
    has type "T", variable has type "Channel"'. Possibly a Strawberry issue
    as strawberry.subscription is a partial function"""

    subscribeChannel: Optional[Channel] = strawberry.subscription(
        resolver=subscribe_channel
    )  # type: ignore


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def putChannels(
        self,
        ids: List[strawberry.ID],
        values: List[str],
        timeout: float = 5.0,
    ) -> Sequence[Channel]:
        """Put a list of values to a list of Channels"""
        store: PluginStore = store_global
        pvs = []
        plugins = set()
        put_values = values
        for id in ids:
            plugin, channel_id = store.plugin_config_id(id)
            pv = channel_id
            assert pv, f"{channel_id} is configured read-only"
            plugins.add(plugin)
            pvs.append(store.transport_pv(pv)[1])
        results = []
        for value in put_values:
            put_value: Union[str, np.ndarray] = value
            if value[:1] in "[{":
                # need to json decode
                put_value = json.loads(value)
                if isinstance(put_value, dict):
                    # decode base64 array
                    dtype = np.dtype(put_value["numberType"].lower())
                    value_b = base64.b64decode(put_value["base64"])
                    # https://stackoverflow.com/a/6485943
                    put_value = np.frombuffer(value_b, dtype=dtype)
            results.append(put_value)
        assert len(results) == len(pvs), "Mismatch in ids and values length"
        assert (
            len(plugins) == 1
        ), "Can only put to pvs with the same transport, not %s" % [
            p.transport for p in plugins
        ]
        await plugins.pop().put_channels(pvs, results, timeout)
        channels: Sequence = [
            GetChannel(channel_id, timeout, store) for channel_id in ids
        ]
        return channels
