import base64
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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


def make_number_format_string(form: DisplayForm, precision: int) -> str:
    return "{:.%df}" % precision


class ChannelFormatter:
    @classmethod
    def for_number(
        cls, form: DisplayForm, precision: int, units: str
    ) -> "ChannelFormatter":
        formatter = cls()
        number_format_string = make_number_format_string(form, precision)
        # number -> string uses given precision
        formatter.to_string = number_format_string.format
        if units:
            number_format_string += " %s" % units
        formatter.to_string_with_units = number_format_string.format
        # number -> float just returns the number
        formatter.to_float = lambda value: value
        return formatter

    @classmethod
    def for_ndarray(
        cls, form: DisplayForm, precision: int, units: str
    ) -> "ChannelFormatter":
        formatter = cls()
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
                base64=base64.b64encode(value).decode(),
            )

        formatter.to_base64_array = ndarray_to_base64_array

        # ndarray -> [str] uses given precision
        def _ndarray_to_string_array(value: np.ndarray, length: int = 0) -> List[str]:
            if length > 0:
                value = value[:length]
            func = number_format_string.format
            return [func(x) for x in value]

        formatter.to_string_array = _ndarray_to_string_array

        return formatter

    @classmethod
    def for_enum(cls, choices: List[str]) -> "ChannelFormatter":
        formatter = cls()
        # enum string value
        formatter.to_string = choices.__getitem__
        # enum index as a float
        formatter.to_float = float
        return formatter

    def to_string_with_units(self, value) -> str:
        return str(value)

    def to_string(self, value) -> str:
        return str(value)

    def to_float(self, value) -> Optional[float]:
        return None

    def to_base64_array(self, value, length: int = 0) -> Optional[Dict[str, str]]:
        return None

    def to_string_array(self, value, length: int = 0) -> Optional[List[str]]:
        return None


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
