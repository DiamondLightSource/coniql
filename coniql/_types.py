from __future__ import annotations

import math
import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Any


from coniql.util import DocEnum, doc_field


class ArrayWrapper:
    """Numpy arrays return ndarrays from == and !=, which conflicts with
    graphql is_nullish(). Can be removed when PR is merged"""
    def __init__(self, array):
        self.array = array

    def __eq__(self, other):
        # Identity is enough for is_nullish()
        return self is other


class NumberType(Enum):
    """The underlying datatype of a number scalar or array"""
    INT8, UINT8, INT16, UINT16, INT32, UINT32, INT64, UINT64, FLOAT32, \
        FLOAT64 = range(10)


class DisplayForm(DocEnum):
    """Instructions for how a number should be formatted for display"""
    DEFAULT = "Use the default representation from value"
    STRING = "Force string representation, most useful for array of bytes"
    BINARY = "Binary, precision determines number of binary digits"
    DECIMAL = "Decimal, precision determines number of digits after " \
        "decimal point"
    HEX = "Hexadecimal, precision determines number of hex digits"
    EXPONENTIAL = "Exponential, precision determines number of digits after " \
        "decimal point"
    ENGINEERING = "Exponential where exponent is multiple of 3, " \
        "precision determines number of digits after decimal point"


class ChannelQuality(DocEnum):
    """Indication of how the current value of a Channel should be interpreted"""
    VALID = "Value is known, valid, nothing is wrong"
    WARNING = "Value is known, valid, but is in the range generating a warning"
    ALARM = "Value is known, valid, but is in the range generating an " \
        "alarm condition"
    INVALID = "Value is known, but not valid, e.g. a write channel before " \
        "its first put"
    UNDEFINED = "The value is unknown, for instance because the channel is " \
        "disconnected"
    CHANGING = "The Channel is currently in the process of being changed"


@dataclass
class Meta:
    description: str = doc_field(
        "A long human readable possibly multi-line description")
    tags: List[str] = doc_field(
        "Free form text tags for widget, user role, port types, etc")
    label: str = doc_field(
        "A short human readable label not longer than a few words")


@dataclass
class NamedMeta:
    """A name-value entry for use in a List of Meta objects"""
    name: str = doc_field(
        "The name of the field the meta represents")
    meta: Meta = doc_field(
        "The meta object that defines it")
    required: bool = doc_field(
        "Whether the given object must exist")


@dataclass
class NamedValue:
    """A name-value entry for use in a List of values"""
    name: str = doc_field("The name of the entry")
    value: Any = doc_field("The value of the entry")


@dataclass
class NumberArray:
    """A base64 encoded array of Numbers with a given datatype"""
    numberType: NumberType = doc_field(
        "The datatype of the input array")
    base64: str = doc_field(
        "A base64 encoded version of the array")


@dataclass
class Range:
    """A range of numbers. Null in either field means unbounded in that
    direction"""
    min: Optional[float] = doc_field(
        "The minimum number of the range")
    max: Optional[float] = doc_field(
        "The maximum number of the range")

    def contains(self, value: float) -> bool:
        rmin = math.nan if self.min is None else self.min
        rmax = math.nan if self.max is None else self.max
        return rmin <= value <= rmax


@dataclass
class ChannelStatus:
    """The current status of a Channel, including alarm and connection status"""
    quality: ChannelQuality = doc_field(
        "Of what quality is the current Channel value")
    message: str = doc_field(
        "Free form text describing the current status")
    mutable: bool = doc_field(
        "Whether the Channel will currently accept mutations")

    @classmethod
    def ok(cls, mutable: bool = False):
        return cls(ChannelQuality.VALID, "", mutable)


@dataclass
class Time:
    """Timestamps indicate when a Field was last updated"""
    seconds: float = doc_field(
        "Seconds since Jan 1, 1970 00:00:00 UTC")
    nanoseconds: int = doc_field(
        "A more accurate version of the nanoseconds part of the seconds field")
    userTag: int = doc_field(
     "An integer value whose interpretation is deliberately undefined")

    @classmethod
    def now(cls):
        now = time.time()
        return Time(now, int(now % 1 / 1e-9), 0)


@dataclass
class NumberDisplay:
    """Information on how to display a numerical value"""
    controlRange: Range = doc_field(
        "The range of values that a control value should be within")
    displayRange: Range = doc_field(
        "Expected range of values that will be produced")
    alarmRange: Range = doc_field(
        "The range outside of which an alarm will be produced")
    warningRange: Range = doc_field(
        "The range outside of which a warning will be produced")
    units: str = doc_field(
        "Physical units for the value field")
    precision: int = doc_field(
        "Number of decimal places to display")
    form: DisplayForm = doc_field(
        "How to display")


@dataclass
class ObjectMeta(Meta):
    """The metadata to describe a generic object"""
    array: bool = doc_field(
        "Whether the value is an array")
    type: str = doc_field(
        "Object type, like String|Boolean|MyEnum|MyType")


@dataclass
class EnumMeta(Meta):
    """The metadata to describe the int index of one of a list of str values"""
    array: bool = doc_field(
        "Whether the value is an array")
    choices: List[str] = doc_field(
        "The possible choices that the string value could take")


@dataclass
class NumberMeta(Meta):
    """The metadata required for a Number Channel"""
    array: bool = doc_field(
        "Whether the value is an array")
    numberType: NumberType = doc_field(
        "The native datatype of the value")
    display: NumberDisplay = doc_field(
        "How should the number be displayed")


@dataclass
class TableMeta(Meta):
    """The metadata required for a Table Channel"""
    columns: List[NamedMeta] = doc_field(
        "Meta objects describing each column of the table")
    idColumns: List[str] = doc_field(
        "Which columns contain IDs, so cannot be modified")


@dataclass
class Channel:
    """A single value with associated time, status and metadata. These values
    can be Null so that in a subscription they are only updated on change"""
    id: str = doc_field(
        "ID that uniquely defines this Channel, normally a PV",
        "")
    meta: Optional[Meta] = doc_field(
        "Metadata telling clients how to display, control, and validate",
        None)
    value: Optional[Any] = doc_field(
        "The current value",
        None)
    time: Optional[Time] = doc_field(
        "When the value was last updated",
        None)
    status: Optional[ChannelStatus] = doc_field(
        "Status of the connection, whether is is mutable, and alarm info",
        None)


@dataclass
class Device:
    """A group of channels and sub-devices"""
    id: str = doc_field(
        "ID that uniquely defines this Channel, normally a PV",
        "")
    meta: Optional[Meta] = doc_field(
        "Metadata telling clients how to display, control, and validate",
        None)
    channels: List[Channel] = doc_field(
        "Channels associated with this device",
        [])
    children: List[Device] = doc_field(
        "Sub-devices associated with this device",
        [])


@dataclass
class FunctionMeta(Meta):
    """The metadata required to describe the arguments taken and returned
    from a function call"""
    takes: List[NamedMeta] = doc_field(
        "Meta objects describing the arguments the function takes")
    defaults: List[NamedValue] = doc_field(
        "The defaults that will be used for non-required fields if not given")
    returns: List[NamedMeta] = doc_field(
        "Meta objects describing the arguments the function returns")


@dataclass
class FunctionLog:
    """A log of arguments that were taken or returned, and the time this
    happened"""
    arguments: List[NamedValue] = doc_field(
        "The arguments that were taken or returned")
    time: Time = doc_field(
        "The time this happened")


@dataclass
class Function:
    """A function that on its own has no state, no current value. It may keep
    track of the last call arguments, return value and status. The values
    can be Null so that in a subscription they are only updated on change"""
    id: str = doc_field(
        "ID that uniquely defines this Method",
        "")
    meta: Optional[FunctionMeta] = doc_field(
        "Metadata telling clients what arguments it takes and returns",
        None)
    took: Optional[FunctionLog] = doc_field(
        "Log of the arguments taken and the time they were received",
        None)
    returned: Optional[FunctionLog] = doc_field(
        "Log of the arguments returned and the time they were returned",
        None)
    status: Optional[ChannelStatus] = doc_field(
        "Status of the connection, whether is is mutable, and error info",
        None)
