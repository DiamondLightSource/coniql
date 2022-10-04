from enum import Enum
from typing import List, Optional

import strawberry
from strawberry.types import Info

import coniql.resolvers as resolver
from coniql.types import Channel, ChannelValue


# Numeric type for arrays of numbers
@strawberry.enum
class NumberType(Enum):
    INT8 = "INT8"
    UINT8 = "UINT8"
    INT16 = "INT16"
    UINT16 = "UINT16"
    INT32 = "INT32"
    UINT32 = "UINT32"
    INT64 = "INT64"
    UINT64 = "UINT64"
    FLOAT32 = "FLOAT32"
    FLOAT64 = "FLOAT64"


# What access role has the Channel
@strawberry.enum
class ChannelRole(Enum):
    RO = "RO"
    WO = "WO"
    RW = "RW"


# Widget that should be used to display a Channel
@strawberry.enum
class Widget(Enum):
    # Editable text input
    TEXTINPUT = "TEXTINPUT"
    # Read-only text display
    TEXTUPDATE = "TEXTUPDATE"
    # Multiline read-only text display
    MULTILINETEXTUPDATE = "MULTILINETEXTUPDATE"
    # Read-only LED indicator
    LED = "LED"
    # Editable combo-box style menu for selecting between fixed choices
    COMBO = "COMBO"
    # Editable check box
    CHECKBOX = "CHECKBOX"
    # Editable progress type bar
    BAR = "BAR"
    # Clickable button to send default value to Channel
    BUTTON = "BUTTON"
    # X-axis for lines on a graph. Only valid within a Group with widget Plot
    PLOTX = "PLOTX"
    # Y-axis for a line on a graph. Only valid within a Group with widget Plot
    PLOTY = "PLOTY"


# Instructions for how a number should be formatted for display
@strawberry.enum
class DisplayForm(Enum):
    # Use the default representation from value
    DEFAULT = "DEFAULT"
    # Force string representation, most useful for array of bytes
    STRING = "STRING"
    # Binary, precision determines number of binary digits
    BINARY = "BINARY"
    # Decimal, precision determines number of digits after decimal point
    DECIMAL = "DECIMAL"
    # Hexadecimal, precision determines number of hex digits
    HEX = "HEX"
    # Exponential, precision determines number of digits after decimal point
    EXPONENTIAL = "EXPONENTIAL"
    # Exponential where exponent is multiple of 3, precision determines number
    # of digits after decimal point
    ENGINEERING = "ENGINEERING"


# Schema
@strawberry.type
class Range:
    # The minimum number that is in this range
    min: float
    # The maximum that is in this range
    max: float


@strawberry.enum
class ChannelQuality(Enum):
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


# Base-64 encodable numeric array
@strawberry.type
class Base64Array:
    # Type of the native array
    numberType: NumberType
    # Base64 encoded version of the array
    base64: str


@strawberry.type
class ChannelValue:
    # The current value formatted as a Float, Null if not expressable
    @strawberry.field
    def float(self) -> Optional[float]:
        return resolver.channel_value_float(self)

    # The current value formatted as a string
    @strawberry.field
    def string(self, units: bool = False) -> str:
        return resolver.channel_value_string(self, units)

    @strawberry.field
    async def base64Array(self, length: int = 0) -> Optional[Base64Array]:
        return await resolver.channel_value_base64_array(self, length)


@strawberry.type
class ChannelStatus:
    # Of what quality is the current Channel value
    quality: ChannelQuality
    # Free form text describing the current status
    message: str
    # Whether the Channel will currently accept mutations
    mutable: bool


@strawberry.type
class ChannelTime:
    # Floating point number of seconds since Jan 1, 1970 00:00:00 UTC
    seconds: float
    # A more accurate version of the nanoseconds part of the seconds field
    nanoseconds: int
    # An integer value whose interpretation is deliberately undefined
    userTag: int
    # The timestamp as a datetime object
    # datetime: datetime


@strawberry.type
class ChannelDisplay:
    # A human readable possibly multi-line description for a tooltip
    description: str
    # What access role does the Channel have
    role: ChannelRole
    # Default widget to display this Channel
    widget: Optional[Widget]
    # If numeric, the range the put value should be within
    controlRange: Optional[Range]
    # If numeric, the range the current value should be within
    displayRange: Optional[Range]
    # If numeric, the range outside of which an alarm will be produced
    alarmRange: Optional[Range]
    # If numeric, the range outside of which a warning will be produced
    warningRange: Optional[Range]
    # If numeric, the physical units for the value field
    units: Optional[str]
    # If numeric, the number of decimal places to display
    precision: Optional[int]
    # If numeric, how should value be displayed
    form: Optional[DisplayForm]
    # If given, the value should be one of these choices
    choices: Optional[List[str]]


@strawberry.type
class Channel:
    # ID that uniquely defines this Channel, normally a PV
    id: strawberry.ID

    # The current value of this channel
    @strawberry.field
    def value(self) -> Optional[ChannelValue]:
        return resolver.channel_value(self)

    # When was the value last updated
    time: ChannelTime

    # Status of the connection, whether is is mutable, and alarm info
    @strawberry.field
    def status(self) -> ChannelStatus:
        return resolver.channel_status(self)

    # How should the Channel be displayed
    @strawberry.field
    def display(self) -> ChannelDisplay:
        return resolver.channel_display(self)


@strawberry.type
class Query:
    # Get the current value of a Channel
    @strawberry.field
    def getChannel(
        self, info: Info, id: strawberry.ID, timeout: float = 5.0
    ) -> Channel:
        return resolver.get_channel(id, timeout, info.context["ctx"])


@strawberry.type
class Subscription:
    # Subscribe to changes in top level fields of Channel,
    # if they haven't changed they will be Null
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
