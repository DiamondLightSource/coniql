from enum import Enum, auto
from typing import List, Optional

import base64
import strawberry
from strawberry.types import Info

import coniql.resolvers as resolver
from coniql.types import Channel, ChannelValue



# Numeric type for arrays of numbers
@strawberry.enum
class NumberType(Enum):
    INT8 = auto()
    UINT8 = auto()
    INT16 = auto()
    UINT16 = auto()
    INT32 = auto()
    UINT32 = auto()
    INT64 = auto()
    UINT64 = auto()
    FLOAT32 = auto()
    FLOAT64 = auto()


# Schema
@strawberry.type
class Range:
    # "The minimum number that is in this range"
    min: float
    # "The maximum that is in this range"
    max: float


@strawberry.enum
class ChannelQuality(Enum):
    # "Value is known, valid, nothing is wrong"
    VALID = auto()
    # "Value is known, valid, but is in the range generating a warning"
    WARNING = auto()
    # "Value is known, valid, but is in the range generating an alarm condition"
    ALARM = auto()
    # "Value is known, but not valid, e.g. a RW before its first put"
    INVALID = auto()
    # "The value is unknown, for instance because the channel is disconnected"
    UNDEFINED = auto()
    # "The Channel is currently in the process of being changed"
    CHANGING = auto()


# Base-64 encodable numeric array
@strawberry.type
class Base64Array:
    # Type of the native array
    numberType: NumberType

    # Base64 encoded version of the array
    base64: str


@strawberry.type
class ChannelValue:
    # "The current value formatted as a string"
    # @strawberry.field
    # def string(self,
    #    #"Whether to include the units in the string"
    #    units: bool = False) -> str

    # "The current value formatted as a Float, Null if not expressable"
    @strawberry.field
    def float(self) -> Optional[float]:
        return resolver.channel_value_float(self)
    @strawberry.field
    def string(self, units: bool = False) -> str:
        return resolver.channel_value_string(self, units)
    @strawberry.field
    async def base64Array(self, length: int = 0) -> Optional[Base64Array]:
        return await resolver.channel_value_base64_array(self, length)


@strawberry.type
class ChannelStatus:
    # "Of what quality is the current Channel value"
    quality: ChannelQuality
    # "Free form text describing the current status"
    message: str
    # "Whether the Channel will currently accept mutations"
    mutable: bool


@strawberry.type
class ChannelTime:
    # "Floating point number of seconds since Jan 1, 1970 00:00:00 UTC"
    seconds: float
    # "A more accurate version of the nanoseconds part of the seconds field"
    nanoseconds: int
    # "An integer value whose interpretation is deliberately undefined"
    userTag: int
    # "The timestamp as a datetime object"
    # datetime: datetime


@strawberry.type
class ChannelDisplay:
    # "A human readable possibly multi-line description for a tooltip"
    description: str


@strawberry.type
class Channel:
    # "ID that uniquely defines this Channel, normally a PV"
    id: strawberry.ID

    # "The current value of this channel"
    @strawberry.field
    def value(self) -> Optional[ChannelValue]:
        return resolver.channel_value(self)

    # "When was the value last updated"
    time: ChannelTime
    # "Status of the connection, whether is is mutable, and alarm info"
    status: ChannelStatus
    # "How should the Channel be displayed"
    display: ChannelDisplay


@strawberry.type
class Query:
    # "Get the current value of a Channel"
    @strawberry.field
    def getChannel(
        self, info: Info, id: strawberry.ID, timeout: float = 5.0
    ) -> Channel:
        return resolver.get_channel(id, timeout, info.context["ctx"])


@strawberry.type
class Subscription:
    # "Subscribe to changes in top level fields of Channel,
    # if they haven't changed they will be Null"
    @strawberry.subscription
    async def subscribeChannel(self, info: Info, id: strawberry.ID) -> Channel:
        return resolver.subscribe_channel(id, info.context["ctx"])


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def putChannels(
        self,
        info: Info,
        ids: List[strawberry.ID],
        values: List[str],
        timeout: float = 5.0,
    ) -> List[Channel]:
        return await resolver.put_channel(ids, values, timeout, info.context["ctx"])
