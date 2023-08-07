import base64
import math
import time
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, Callable, List, Optional

import numpy as np
import strawberry

from .coniql_schema import DisplayForm, Widget


@strawberry.type
@dataclass
class Range:
    """
    A range of numbers. Null in either field means unbounded in that direction.
    A value is in range if min <= value <= max
    """

    # The minimum number that is in this range
    min: float
    # The maximum that is in this range
    max: float

    def contains(self, value: float) -> bool:
        rmin = math.nan if self.min is None else self.min
        rmax = math.nan if self.max is None else self.max
        return rmin <= value <= rmax


class ChannelQuality(IntEnum):
    """
    Indication of how the current value of a Channel should be interpreted

    Note: The values align to the "menuAlarmSevr" enum in EPICS, with a couple of
    extension values.
    """

    # Value is known, valid, nothing is wrong
    VALID = 0
    # Value is known, valid, but is in the range generating a warning
    WARNING = 1
    # Value is known, valid, but is in the range generating an alarm condition
    ALARM = 2
    # Value is known, but not valid, e.g. a RW before its first put
    INVALID = 3
    # The value is unknown, for instance because the channel is disconnected
    UNDEFINED = 4
    # The Channel is currently in the process of being changed
    CHANGING = 5

    def __str__(self):
        # Returns the Enum item as a string e.g. "VALID", rather than integer value
        return self.name


# Map from display form to DisplayForm enum
DISPLAY_FORM_MAP = [
    DisplayForm.DEFAULT,
    DisplayForm.STRING,
    DisplayForm.BINARY,
    DisplayForm.DECIMAL,
    DisplayForm.HEX,
    DisplayForm.EXPONENTIAL,
    DisplayForm.ENGINEERING,
]

# GraphQL schema has a variable named 'float', which is an inbuilt type in Python
# and can lead to problems when used in type hinting. Create alias inbuilt float type.
TypeFloatAlias = float


@strawberry.type
class ChannelDisplay:
    # A human readable possibly multi-line description for a tooltip
    description: str
    # What access role does the Channel have
    role: "ChannelRole"
    # Default widget to display this Channel
    widget: Optional[Widget]
    # If numeric, the range the put value should be within
    controlRange: Optional[Range] = None
    # If numeric, the range the current value should be within
    displayRange: Optional[Range] = None
    # If numeric, the range outside of which an alarm will be produced
    alarmRange: Optional[Range] = None
    # If numeric, the range outside of which a warning will be produced
    warningRange: Optional[Range] = None
    # If numeric, the physical units for the value field
    units: Optional[str] = None
    # If numeric, the number of decimal places to display
    precision: Optional[int] = None
    # If numeric, how should value be displayed
    form: Optional[DisplayForm] = None
    # If given, the value should be one of these choices
    choices: Optional[List[str]] = None


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


@strawberry.enum
class ChannelRole(Enum):
    """
    What access role has the Channel
    """

    RO = "RO"
    WO = "WO"
    RW = "RW"


@strawberry.type
@dataclass
class Base64Array:
    # Type of the native array
    numberType: NumberType
    # Base64 encoded version of the array
    base64: str


def make_number_format_string(precision: Optional[int]) -> str:
    assert precision is not None
    return "{:.%df}" % precision


def return_if_number(value):
    if math.isfinite(value):
        return value


def return_none(*args, **kwargs):
    return None


class ChannelFormatter:
    @classmethod
    def for_number(
        cls, precision: Optional[int], units: Optional[str]
    ) -> "ChannelFormatter":
        number_format_string = make_number_format_string(precision)
        if units:
            units_format_string = f"{number_format_string} {units}"
        else:
            units_format_string = number_format_string
        formatter = cls(
            # number -> string uses given precision
            to_string=number_format_string.format,
            to_string_with_units=units_format_string.format,
            # number -> float just returns the number
            to_float=return_if_number,
        )
        return formatter

    @classmethod
    def for_ndarray(
        cls, precision: Optional[int], units: Optional[str]
    ) -> "ChannelFormatter":
        number_format_string = make_number_format_string(precision)

        # ndarray -> base64 encoded array
        def ndarray_to_base64_array(value: np.ndarray, length: int = 0) -> Base64Array:
            if length > 0:
                value = value[:length]
            return Base64Array(
                value.dtype.name.upper(), base64.b64encode(value.tobytes()).decode()
            )

        # ndarray -> [str] uses given precision
        def ndarray_to_string_array(value: np.ndarray, length: int = 0) -> List[str]:
            if length > 0:
                value = value[:length]
            func = number_format_string.format
            return [func(x) for x in value]

        formatter = cls(
            to_base64_array=ndarray_to_base64_array,
            to_string_array=ndarray_to_string_array,
        )

        return formatter

    @classmethod
    def for_enum(cls, choices: List[str]) -> "ChannelFormatter":
        formatter = cls(
            # enum string value
            to_string=choices.__getitem__,
            # enum index as a float
            to_float=float,
        )
        return formatter

    def __init__(
        self,
        to_string: Callable[[Any], str] = str,
        to_string_with_units: Callable[[Any], str] = str,
        to_float: Callable[[Any], Optional[float]] = return_none,
        to_base64_array: Callable[[Any, int], Optional[Base64Array]] = return_none,
        to_string_array: Callable[[Any, int], Optional[List[str]]] = return_none,
    ):
        self.to_string = to_string
        self.to_string_with_units = to_string_with_units
        self.to_float = to_float
        self.to_base64_array = to_base64_array
        self.to_string_array = to_string_array


@dataclass
class ChannelStatus:
    """
    The current status of a Channel, including alarm and connection status
    """

    # Of what quality is the current Channel value
    quality: str
    # Free form text describing the current status
    message: str
    # Whether the Channel will currently accept mutations
    mutable: bool

    @classmethod
    def valid(cls, mutable: bool = False) -> "ChannelStatus":
        return cls("VALID", "", mutable)

    @classmethod
    def warning(cls, message: str, mutable: bool = False) -> "ChannelStatus":
        return cls("WARNING", message, mutable)

    @classmethod
    def alarm(cls, message: str, mutable: bool = False) -> "ChannelStatus":
        return cls("ALARM", message, mutable)

    @classmethod
    def invalid(cls, message: str, mutable: bool = False) -> "ChannelStatus":
        return cls("INVALID", message, mutable)

    @classmethod
    def undefined(cls, message: str, mutable: bool = False) -> "ChannelStatus":
        return cls("UNDEFINED", message, mutable)

    @classmethod
    def changing(cls, message: str, mutable: bool = False) -> "ChannelStatus":
        return cls("CHANGING", message, mutable)


@strawberry.type
@dataclass
class ChannelTime:
    """
    Timestamp indicating when a value was last updated
    """

    # Floating point number of seconds since Jan 1, 1970 00:00:00 UTC
    seconds: float
    # A more accurate version of the nanoseconds part of the seconds field
    nanoseconds: int
    # An integer value whose interpretation is deliberately undefined
    userTag: int

    @classmethod
    def now(cls) -> "ChannelTime":
        now = time.time()
        return cls(now, int(now % 1 / 1e-9), 0)


@dataclass
class ChannelValue:
    value: Any
    formatter: ChannelFormatter = ChannelFormatter()


class Channel:
    def get_id(self) -> Optional[str]:
        raise NotImplementedError(self)

    def get_value(self) -> Optional[ChannelValue]:
        raise NotImplementedError(self)

    def get_time(self) -> Optional[ChannelTime]:
        raise NotImplementedError(self)

    def get_status(self) -> Optional[ChannelStatus]:
        raise NotImplementedError(self)

    def get_display(self) -> Optional[ChannelDisplay]:
        raise NotImplementedError(self)
