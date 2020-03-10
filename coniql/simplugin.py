from __future__ import annotations

import asyncio
import json
import math
import time
from asyncio import Queue
import dataclasses
from dataclasses import dataclass
from typing import Dict, Type, Set, TypeVar, Generic, List, Any

import numpy as np

from coniql.util import doc_field
from .plugin import Plugin
from ._types import (
    NumberMeta,
    Channel,
    NumberType,
    NumberDisplay,
    Range,
    Time,
    ChannelStatus,
    ChannelQuality,
    DisplayForm,
    ArrayWrapper,
    Function,
    NamedMeta,
    ObjectMeta,
    FunctionMeta,
    NamedValue,
)

# How long to keep Sim alive after the last listener has gone
SIM_DESTROY_TIMEOUT = 10

# Map of channel_id func to its Sim class
CHANNEL_CLASSES: Dict[str, Type["SimChannel"]] = {}

# Map of channel_id func to its callable function
FUNCTION_CLASSES: Dict[str, Type["SimFunction"]] = {}


def register_channel(func: str):
    def decorator(cls: Type[SimChannel]):
        CHANNEL_CLASSES[func] = cls
        return cls

    return decorator


def register_function(func: str):
    def decorator(cls: Type[SimFunction]):
        FUNCTION_CLASSES[func] = cls
        return cls

    return decorator


class SimChannel:
    def __init__(self, update_seconds: float = 1.0):
        self.update_seconds = update_seconds
        self.channel = Channel(time=Time.now(), status=ChannelStatus.ok())

    def compute_changes(self, **changes):
        changes["time"] = Time.now()
        for k, v in list(changes.items()):
            is_not_equal = v != getattr(self.channel, k)
            if hasattr(is_not_equal, "any"):
                is_not_equal = is_not_equal.any()
            if is_not_equal:
                setattr(self.channel, k, v)
            else:
                changes.pop(k)
        return changes


def make_number_display(
    min_value: float,
    max_value: float,
    warning_percent: float = 100,
    alarm_percent: float = 100,
) -> NumberDisplay:
    display_range = max_value - min_value
    alarm_range = display_range * alarm_percent / 100
    warning_range = display_range * warning_percent / 100
    display = NumberDisplay(
        controlRange=Range(min_value, max_value),
        displayRange=Range(min_value, max_value),
        warningRange=Range(
            min_value + (display_range - warning_range) / 2,
            max_value - (display_range - warning_range) / 2,
        ),
        alarmRange=Range(
            min_value + (display_range - alarm_range) / 2,
            max_value - (display_range - alarm_range) / 2,
        ),
        units="",
        precision=0,
        form=DisplayForm.DEFAULT,
    )
    return display


@register_channel("sine")
class SineSimChannel(SimChannel):
    """Create a simulated float sine value

    Args:
        min_value: The minimum output value
        max_value: The maximum output value
        steps: The number of steps taken to produce a complete sine wave
        update_seconds: The time between each step
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(
        self,
        min_value: float = -5.0,
        max_value: float = 5.0,
        steps: float = 10.0,
        update_seconds: float = 1.0,
        warning_percent: float = 80.0,
        alarm_percent: float = 90.0,
    ):
        super(SineSimChannel, self).__init__(update_seconds)
        assert max_value > min_value, "max_value %s is not > min_value %s" % (
            max_value,
            min_value,
        )
        self.min = min_value
        self.range = max_value - min_value
        self.step = 2 * math.pi / max(steps, 1)
        self.x = 0
        self.channel.meta = NumberMeta(
            description="A Sine value generator",
            label="Sine Value",
            tags=["widget:textupdate"],
            array=False,
            numberType=NumberType.FLOAT64,
            display=make_number_display(
                min_value, max_value, warning_percent, alarm_percent
            ),
        )
        self.channel.value = 0

    def compute_changes(self):
        value = self.min + (math.sin(self.x) + 1.0) / 2.0 * self.range
        self.x += self.step
        display: NumberDisplay = self.channel.meta.display
        if not display.alarmRange.contains(value):
            status = ChannelStatus(
                ChannelQuality.ALARM, "Outside alarm range", mutable=False
            )
        elif not display.warningRange.contains(value):
            status = ChannelStatus(
                ChannelQuality.WARNING, "Outside warning range", mutable=False
            )
        else:
            status = ChannelStatus.ok(mutable=False)
        return super(SineSimChannel, self).compute_changes(value=value, status=status)


@register_channel("sinewave")
class SineWaveSimChannel(SimChannel):
    """Create a simulated float waveform

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(
        self,
        period_seconds: float = 1.0,
        sample_wavelength: float = 10.0,
        size: int = 50,
        update_seconds: float = 1.0,
        min_value: float = -5.0,
        max_value: float = 5.0,
        warning_percent: float = 80.0,
        alarm_percent: float = 90.0,
    ):
        super(SineWaveSimChannel, self).__init__(update_seconds)
        assert max_value > min_value, "max_value %s is not > min_value %s" % (
            max_value,
            min_value,
        )
        self.min = min_value
        self.range = max_value - min_value
        self.period = max(period_seconds, 0.001)
        self.size = size
        self.wavelength = sample_wavelength
        self.start = time.time()
        self.channel.meta = NumberMeta(
            description="A Sine waveform generator",
            label="Sine Waveform",
            tags=["widget:graph"],
            array=True,
            numberType=NumberType.FLOAT64,
            display=make_number_display(
                min_value, max_value, warning_percent, alarm_percent
            ),
        )
        self.channel.value = ArrayWrapper(np.zeros(size, dtype=np.float64))

    def compute_changes(self):
        t = time.time() - self.start
        x0 = t / self.period
        x = 2 * math.pi * (x0 + np.arange(self.size) / self.wavelength)
        value = ArrayWrapper(self.min + (np.sin(x) + 1.0) / 2.0 * self.range)
        return super(SineWaveSimChannel, self).compute_changes(value=value)


@register_channel("sinewavesimple:1")
class SineWaveSimple1SimChannel(SimChannel):
    """Create a simulated float waveform with a simple distribution of values

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(
        self,
        period_seconds: float = 1.0,
        sample_wavelength: float = 10.0,
        size: int = 1,
        update_seconds: float = 1.0,
        min_value: float = -5.0,
        max_value: float = 5.0,
        warning_percent: float = 80.0,
        alarm_percent: float = 90.0,
    ):
        super(SineWaveSimple1SimChannel, self).__init__(update_seconds)
        assert max_value > min_value, "max_value %s is not > min_value %s" % (
            max_value,
            min_value,
        )
        self.min = min_value
        self.range = max_value - min_value
        self.period = max(period_seconds, 0.001)
        self.size = size
        self.wavelength = sample_wavelength
        self.start = time.time()
        self.channel.meta = NumberMeta(
            description="A Sine waveform generator",
            label="Sine Waveform",
            tags=["widget:graph"],
            array=True,
            numberType=NumberType.FLOAT64,
            display=make_number_display(
                min_value, max_value, warning_percent, alarm_percent
            ),
        )
        # Create an array of values equal to the size
        self.channel.value = ArrayWrapper(
            np.array([x for x in range(self.size)], dtype=np.float64)
        )

    def compute_changes(self):
        # Roll the array around by one element
        value = ArrayWrapper(np.roll(self.channel.value.array, 1))
        return super(SineWaveSimple1SimChannel, self).compute_changes(value=value)


@register_channel("sinewavesimple:10")
class SineWaveSimple10SimChannel(SineWaveSimple1SimChannel):
    """Create a simulated float waveform with a simple distribution of values

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(self, **kwargs):
        super(SineWaveSimple10SimChannel, self).__init__(**kwargs, size=10)


@register_channel("sinewavesimple:100")
class SineWaveSimple100SimChannel(SineWaveSimple1SimChannel):
    """Create a simulated float waveform with a simple distribution of values

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(self, **kwargs):
        super(SineWaveSimple100SimChannel, self).__init__(**kwargs, size=100)


@register_channel("sinewavesimple:1000")
class SineWaveSimple1000SimChannel(SineWaveSimple1SimChannel):
    """Create a simulated float waveform with a simple distribution of values

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(self, **kwargs):
        super(SineWaveSimple1000SimChannel, self).__init__(**kwargs, size=1000)


@register_channel("sinewavesimple:10000")
class SineWaveSimple10000SimChannel(SineWaveSimple1SimChannel):
    """Create a simulated float waveform with a simple distribution of values

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(self, **kwargs):
        super(SineWaveSimple10000SimChannel, self).__init__(**kwargs, size=10000)


@register_channel("sinewavesimple:100000")
class SineWaveSimple100000SimChannel(SineWaveSimple1SimChannel):
    """Create a simulated float waveform with a simple distribution of values

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(self, **kwargs):
        super(SineWaveSimple100000SimChannel, self).__init__(**kwargs, size=100000)


@register_channel("sinewavesimple:1000000")
class SineWaveSimple1000000SimChannel(SineWaveSimple1SimChannel):
    """Create a simulated float waveform with a simple distribution of values

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """

    def __init__(self, **kwargs):
        super(SineWaveSimple1000000SimChannel, self).__init__(**kwargs, size=1000000)


T = TypeVar("T")
R = TypeVar("R")


def _fields_to_metas(fields: List[dataclasses.Field]) -> List[NamedMeta]:
    ret: List[NamedMeta] = []
    for field in fields:
        # TODO: generalize this
        if field.type == "str":
            meta = ObjectMeta(
                description=field.metadata["docstring"],
                # TODO: need to guess widget depending on direction
                tags=["widget:textinput"],
                label=field.name,
                array=False,
                type="String",
            )
        elif field.type == "float":
            meta = NumberMeta(
                description=field.metadata["docstring"],
                # TODO: need to guess widget depending on direction
                tags=["widget:textinput"],
                label=field.name,
                array=False,
                numberType=NumberType.FLOAT64,
                display=make_number_display(0, math.nan, math.nan, math.nan),
            )
        else:
            raise TypeError("Can't deal with %r" % field.type)
        ret.append(
            NamedMeta(
                name=field.name,
                meta=meta,
                required=field.default is not dataclasses.MISSING,
            )
        )
    return ret


def _fields_to_defaults(fields: List[dataclasses.Field]) -> List[NamedValue]:
    ret: List[NamedValue] = []
    for field in fields:
        if field.default is not dataclasses.MISSING:
            ret.append(NamedValue(name=field.name, value=field.default))
    return ret


class SimFunction:
    Takes: Type[T]
    Returns: Type[R]

    function: Function = None

    def __init__(self):
        self.function = Function(
            meta=FunctionMeta(
                label=self.__class__.__name__,
                tags=[],
                description=self.__doc__,
                takes=_fields_to_metas(dataclasses.fields(self.Takes)),
                defaults=_fields_to_defaults(dataclasses.fields(self.Takes)),
                returns=_fields_to_metas(dataclasses.fields(self.Returns)),
            ),
            status=ChannelStatus.ok(mutable=True),
        )

    async def __call__(self, arguments: T) -> R:
        raise NotImplementedError(self)


@register_function("hello")
class Hello(SimFunction):
    """Say hello to someone"""

    @dataclass
    class Takes:
        name: str = doc_field("The name of the person to say hello to")
        sleep: float = doc_field("How long to wait before returning", 0)

    @dataclass
    class Returns:
        greeting: str = doc_field("The greeting")

    async def __call__(self, arguments: Takes) -> Returns:
        print(arguments)
        await asyncio.sleep(arguments.sleep)
        return self.Returns(greeting=f"Hello {arguments.name}")


class SimPlugin(Plugin):
    def __init__(self):
        # {channel_id: SimChannel}
        self.sim_channels: Dict[str, SimChannel] = {}
        # {function_id: SimFunction}
        self.sim_functions: Dict[str, SimFunction] = {}
        # {channel_id: {queue_for_each_listener}}
        self.listeners: Dict[str, Set[Queue]] = {}

    async def _start_computing(self, channel_id: str):
        sim = self.sim_channels[channel_id]
        next_compute = time.time()
        last_had_listeners = next_compute
        while next_compute - last_had_listeners < SIM_DESTROY_TIMEOUT:
            next_compute += sim.update_seconds
            await asyncio.sleep(next_compute - time.time())
            channel = Channel(**sim.compute_changes())
            for q in self.listeners[channel_id]:
                last_had_listeners = next_compute
                await q.put(channel)
        # no-one listening, remove sim
        del self.sim_channels[channel_id]
        del self.listeners[channel_id]

    def _get_sim_channel(self, channel_id: str) -> SimChannel:
        if channel_id not in self.sim_channels:
            if "(" in channel_id:
                assert channel_id.endswith(")"), (
                    "Missing closing bracket in %r" % channel_id
                )
                func, param_str = channel_id[:-1].split("(", 1)
                parameters = [float(param.strip()) for param in param_str.split(",")]
            else:
                func = channel_id
                parameters = []
            cls = CHANNEL_CLASSES[func]
            self.sim_channels[channel_id] = cls(*parameters)
            self.listeners[channel_id] = set()
            asyncio.create_task(self._start_computing(channel_id))
        return self.sim_channels[channel_id]

    def _get_sim_function(self, function_id: str) -> SimFunction:
        if function_id not in self.sim_functions:
            cls = FUNCTION_CLASSES[function_id]
            self.sim_functions[function_id] = cls()
        return self.sim_functions[function_id]

    async def get_channel(self, channel_id: str, timeout: float) -> Channel:
        sim = self._get_sim_channel(channel_id)
        return sim.channel

    async def get_function(self, function_id: str, timeout: float) -> Function:
        sim = self._get_sim_function(function_id)
        return sim.function

    async def call_function(self, function_id: str, arguments, timeout: float) -> Any:
        sim = self._get_sim_function(function_id)
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        takes = sim.Takes(**arguments)
        ret = await sim(takes)
        # ret = dataclasses.asdict(ret)

        return ret

    async def subscribe_channel(self, channel_id: str):
        q = asyncio.Queue()
        try:
            sim = self._get_sim_channel(channel_id)
            self.listeners[channel_id].add(q)
            yield sim.channel
            while True:
                yield await q.get()
        finally:
            self.listeners[channel_id].remove(q)
