import asyncio
import base64
import datetime
import json
from typing import AsyncGenerator, List, Optional, Sequence, Set, Union

import numpy as np
import strawberry

from coniql.caplugin import CAPlugin
from coniql.plugin import Plugin, PluginStore
from coniql.simplugin import SimPlugin
from coniql.types import Base64Array as TypeBase64Array
from coniql.types import Channel as TypeChannel
from coniql.types import ChannelDisplay
from coniql.types import ChannelStatus as TypeChannelStatus
from coniql.types import ChannelTime as TypeChannelTime
from coniql.types import ChannelValue as TypeChannelValue
from coniql.types import TypeFloatAlias

store_global = PluginStore()
store_global.add_plugin("ssim", SimPlugin())
store_global.add_plugin("ca", CAPlugin(), set_default=True)


def resolve_float(root: TypeChannelValue) -> Optional[float]:
    return root.formatter.to_float(root.value)


def resolve_string(root: TypeChannelValue, units: bool = False) -> Optional[str]:
    if units:
        return root.formatter.to_string_with_units(root.value)
    else:
        return root.formatter.to_string(root.value)


def resolve_base64Array(
    root: TypeChannelValue, length: int = 0
) -> Optional[TypeBase64Array]:
    return root.formatter.to_base64_array(root.value, length)


def resolve_stringArray(root: TypeChannelValue, length: int = 0) -> Optional[List[str]]:
    return root.formatter.to_string_array(root.value, length)


@strawberry.type
class ChannelValue:
    """
    Value that can be formatted in a number of ways
    """

    # The current value formatted as a Float, Null if not expressable
    float: Optional[TypeFloatAlias] = strawberry.field(resolver=resolve_float)
    # The current value formatted as a string
    string: Optional[str] = strawberry.field(resolver=resolve_string)
    # Array of base64 encoded numbers, Null if not expressable
    base64Array: Optional[TypeBase64Array] = strawberry.field(
        resolver=resolve_base64Array
    )
    # Array of strings, Null if not expressable
    stringArray: Optional[List[str]] = strawberry.field(resolver=resolve_stringArray)


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


def resolver_id(root: "DeferredChannel") -> Optional[str]:
    channel = root.get_channel()
    return channel.get_id()


def resolver_value(root: "DeferredChannel") -> Optional[TypeChannelValue]:
    channel = root.get_channel()
    return channel.get_value()


def resolver_time(root: "DeferredChannel") -> Optional[TypeChannelTime]:
    channel = root.get_channel()
    return channel.get_time()


def resolver_status(root: "DeferredChannel") -> Optional[TypeChannelStatus]:
    channel = root.get_channel()
    return channel.get_status()


def resolver_display(root: "DeferredChannel") -> Optional[ChannelDisplay]:
    channel = root.get_channel()
    return channel.get_display()


@strawberry.type
class Channel(TypeChannel):
    """
    A single value with associated time, status and metadata. These values
    can be Null so that in a subscription they are only updated on change
    """

    def __init__(self, plugin_channel: TypeChannel):
        self.parentChannel = plugin_channel

    def get_id(self) -> Optional[str]:
        return self.parentChannel.get_id()

    def get_value(self) -> Optional[TypeChannelValue]:
        return self.parentChannel.get_value()

    def get_time(self) -> Optional[TypeChannelTime]:
        return self.parentChannel.get_time()

    def get_status(self) -> Optional[TypeChannelStatus]:
        return self.parentChannel.get_status()

    def get_display(self) -> Optional[ChannelDisplay]:
        return self.parentChannel.get_display()

    # ID that uniquely defines this Channel, normally a PV
    id: Optional[str] = strawberry.field(resolver=resolver_id)
    # The current value of this channel
    value: Optional[ChannelValue] = strawberry.field(
        resolver=resolver_value
    )  # type: ignore
    # When was the value last updated
    time: Optional[ChannelTime] = strawberry.field(
        resolver=resolver_time
    )  # type: ignore
    # Status of the connection, whether is is mutable, and alarm info
    status: Optional[ChannelStatus] = strawberry.field(
        resolver=resolver_status
    )  # type: ignore
    # How should the Channel be displayed
    display: Optional[ChannelDisplay] = strawberry.field(resolver=resolver_display)


class DeferredChannel(Channel):
    id: str
    lock: asyncio.Lock
    channel: Optional[Channel] = None

    async def populate_channel(self) -> Channel:
        raise NotImplementedError(self)

    def get_channel(self) -> Channel:
        assert self.channel
        return self.channel


class GetChannel(DeferredChannel):
    def __init__(self, channel_id: str, timeout: float, store: PluginStore):
        self.plugin, self.id = store.plugin_config_id(channel_id)
        # Remove the transport prefix from the read pv
        self.pv = store.transport_pv(channel_id)[1]
        self.timeout = timeout
        self.lock = asyncio.Lock()

    async def populate_channel(self) -> Channel:
        channel = await self.plugin.get_channel(self.pv, self.timeout)
        # Convert types.Channel object to a Strawberry schema Channel
        strawberry_channel = Channel(channel)
        self.channel = strawberry_channel
        return strawberry_channel


async def get_channel(id: strawberry.ID, timeout: float = 5.0) -> Channel:
    channel = GetChannel(id, timeout, store_global)
    await channel.populate_channel()
    return channel


@strawberry.type
class Query:
    # Get the current value of a Channel
    getChannel: Channel = strawberry.field(resolver=get_channel)


class SubscribeChannel(DeferredChannel):
    def __init__(self, channel_id: str, channel: Channel):
        self.id = channel_id
        self.channel = channel


async def subscribe_channel(id: strawberry.ID) -> AsyncGenerator[Channel, None]:
    """Subscribe to changes in top level fields of Channel,
    if they haven't changed they will be Null"""
    store: PluginStore = store_global
    plugin, channel_id = store.plugin_config_id(id)
    # Remove the transport prefix from the read pv
    pv = store.transport_pv(id)[1]
    async for channel in plugin.subscribe_channel(pv):
        # Convert types.Channel object to a Strawberry schema Channel
        strawberry_channel = Channel(channel)
        yield SubscribeChannel(channel_id, strawberry_channel)


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
        pvs: List[str] = []
        plugins: Set[Plugin] = set()
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
        channels: Sequence[GetChannel] = [
            GetChannel(channel_id, timeout, store) for channel_id in ids
        ]
        for channel in channels:
            await channel.populate_channel()
        return channels
