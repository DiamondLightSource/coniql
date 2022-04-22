import base64
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .coniql_schema import DisplayForm, Widget


@dataclass
class Range:
    min: Optional[float]
    max: Optional[float]

    def contains(self, value: float) -> bool:
        rmin = math.nan if self.min is None else self.min
        rmax = math.nan if self.max is None else self.max
        return rmin <= value <= rmax


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


@dataclass
class ChannelDisplay:
    description: str
    role: str
    widget: Widget
    controlRange: Optional[Range] = None
    displayRange: Optional[Range] = None
    alarmRange: Optional[Range] = None
    warningRange: Optional[Range] = None
    units: Optional[str] = None
    precision: Optional[int] = None
    form: Optional[DisplayForm] = None
    choices: Optional[List[str]] = None


def make_number_format_string(
    form: Optional[DisplayForm], precision: Optional[int]
) -> str:
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
        cls, form: Optional[DisplayForm], precision: Optional[int], units: Optional[str]
    ) -> "ChannelFormatter":
        number_format_string = make_number_format_string(form, precision)
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
        cls, form: Optional[DisplayForm], precision: Optional[int], units: Optional[str]
    ) -> "ChannelFormatter":
        number_format_string = make_number_format_string(form, precision)

        # ndarray -> base64 encoded array
        def ndarray_to_base64_array(
            value: np.ndarray, length: int = 0
        ) -> Optional[Dict[str, str]]:
            if length > 0:
                value = value[:length]
            return dict(
                numberType=value.dtype.name.upper(),
                # https://stackoverflow.com/a/6485943
                base64=base64.b64encode(value.tobytes()).decode(),
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
        to_base64_array: Callable[[Any, int], Optional[Dict[str, str]]] = return_none,
        to_string_array: Callable[[Any, int], Optional[List[str]]] = return_none,
    ):
        self.to_string = to_string
        self.to_string_with_units = to_string_with_units
        self.to_float = to_float
        self.to_base64_array = to_base64_array
        self.to_string_array = to_string_array


# Map from alarm.severity to ChannelQuality string
CHANNEL_QUALITY_MAP = [
    "VALID",
    "WARNING",
    "ALARM",
    "INVALID",
    "UNDEFINED",
]


@dataclass
class ChannelStatus:
    quality: str
    message: str
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


@dataclass
class ChannelTime:
    seconds: float
    nanoseconds: int
    userTag: int

    @classmethod
    def now(cls):
        now = time.time()
        return cls(now, int(now % 1 / 1e-9), 0)


@dataclass
class ChannelValue:
    value: Any
    formatter: ChannelFormatter = ChannelFormatter()


class Channel:
    def get_value(self) -> Optional[ChannelValue]:
        raise NotImplementedError(self)

    def get_time(self) -> Optional[ChannelTime]:
        raise NotImplementedError(self)

    def get_status(self) -> Optional[ChannelStatus]:
        raise NotImplementedError(self)

    def get_display(self) -> Optional[ChannelDisplay]:
        raise NotImplementedError(self)
