import base64
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class DisplayForm(Enum):
    DEFAULT = "DEFAULT"
    STRING = "STRING"
    BINARY = "BINARY"
    DECIMAL = "DECIMAL"
    HEX = "HEX"
    EXPONENTIAL = "EXPONENTIAL"
    ENGINEERING = "ENGINEERING"


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
    label: str
    description: str
    role: str
    widget: str
    controlRange: Optional[Range] = None
    displayRange: Optional[Range] = None
    alarmRange: Optional[Range] = None
    warningRange: Optional[Range] = None
    units: Optional[str] = None
    precision: Optional[int] = None
    form: Optional[str] = None
    choices: Optional[List[str]] = None

    def _number_format_string(self) -> str:
        assert (
            self.precision is not None
        ), f"Can't make a number formatter without precision of {self}"
        return "{:.%df}" % self.precision

    def _ndarray_to_base64_array(
        self, value: np.ndarray, length: int = 0
    ) -> Optional[Dict[str, str]]:
        if length > 0:
            value = value[:length]
        return dict(
            numberType=value.dtype.name.upper(),
            # https://stackoverflow.com/a/6485943
            base64=base64.b64encode(value).decode(),
        )

    def _ndarray_to_string_array(self, value: np.ndarray, length: int = 0) -> List[str]:
        if length > 0:
            value = value[:length]
        func = self._number_format_string().format
        return [func(x) for x in value]

    def make_number_formatter(self):
        formatter = ChannelFormatter()
        # number -> string uses given precision
        formatter.to_string = self._number_format_string().format
        # number -> float just returns the number
        formatter.to_float = lambda value: value
        return formatter

    def make_ndarray_formatter(self):
        formatter = ChannelFormatter()
        # ndarray -> base64 encoded array
        formatter.to_base64_array = self._ndarray_to_base64_array
        # ndarray -> [str] uses given precision
        formatter.to_string_array = self._ndarray_to_string_array
        return formatter


class ChannelFormatter:
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
    formatter: ChannelFormatter


@dataclass
class Channel:
    id: str
    value: Optional[ChannelValue] = None
    time: Optional[ChannelTime] = None
    status: Optional[ChannelStatus] = None
    display: Optional[ChannelDisplay] = None
