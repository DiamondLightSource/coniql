import asyncio
import math
import time
from asyncio import Queue
from typing import Dict, Type, Set

import numpy as np

from .plugin import Plugin
from ._types import NumberMeta, Channel, NumberType, NumberDisplay, Range, Time, \
    ChannelStatus, ChannelQuality, DisplayForm, ArrayWrapper

# How long to keep Sim alive after the last listener has gone
SIM_DESTROY_TIMEOUT = 10

# Map of channel_id func to its Sim class
CHANNEL_CLASSES: Dict[str, Type['Sim']] = {}


def register(func: str):
    def decorator(cls: Type[Sim]):
        CHANNEL_CLASSES[func] = cls
        return cls

    return decorator


def make_sim_channel(channel_id: str) -> 'Sim':
    if "(" in channel_id:
        assert channel_id.endswith(")"), \
            "Missing closing bracket in %r" % channel_id
        func, param_str = channel_id[:-1].split("(", 1)
        parameters = [
            float(param.strip()) for param in param_str.split(",")]
    else:
        func = channel_id
        parameters = []
    cls = CHANNEL_CLASSES[func]
    return cls(*parameters)


class Sim:
    def __init__(self, update_seconds: float = 1.0):
        self.update_seconds = update_seconds
        self.channel = Channel(
            time=Time.now(),
            status=ChannelStatus.ok()
        )

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


def make_number_display(min_value: float,
                        max_value: float,
                        warning_percent: float = 100,
                        alarm_percent: float = 100) -> NumberDisplay:
    display_range = max_value - min_value
    alarm_range = display_range * alarm_percent / 100
    warning_range = display_range * warning_percent / 100
    display = NumberDisplay(
        controlRange=Range(min_value, max_value),
        displayRange=Range(min_value, max_value),
        warningRange=Range(
            min_value + (display_range - warning_range) / 2,
            max_value - (display_range - warning_range) / 2),
        alarmRange=Range(
            min_value + (display_range - alarm_range) / 2,
            max_value - (display_range - alarm_range) / 2),
        units="",
        precision=0,
        form=DisplayForm.DEFAULT)
    return display


@register("sine")
class SineSim(Sim):
    """Create a simulated float sine value

    Args:
        min_value: The minimum output value
        max_value: The maximum output value
        steps: The number of steps taken to produce a complete sine wave
        update_seconds: The time between each step
        warning_percent: Percentage of the full range, outside this is warning
        alarm_percent: Percentage of the full range, outside this is alarm
    """
    def __init__(self,
                 min_value: float = -5.0,
                 max_value: float = 5.0,
                 steps: float = 10.0,
                 update_seconds: float = 1.0,
                 warning_percent: float = 80.0,
                 alarm_percent: float = 90.0):
        super(SineSim, self).__init__(update_seconds)
        assert max_value > min_value, \
            "max_value %s is not > min_value %s" % (max_value, min_value)
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
                min_value, max_value, warning_percent, alarm_percent))
        self.channel.value = 0

    def compute_changes(self):
        value = self.min + (math.sin(self.x) + 1.0) / 2.0 * self.range
        self.x += self.step
        display: NumberDisplay = self.channel.meta.display
        if not display.alarmRange.contains(value):
            status = ChannelStatus(
                ChannelQuality.ALARM, "Outside alarm range", mutable=False)
        elif not display.warningRange.contains(value):
            status = ChannelStatus(
                ChannelQuality.WARNING, "Outside warning range", mutable=False)
        else:
            status = ChannelStatus.ok(mutable=False)
        return super(SineSim, self).compute_changes(value=value, status=status)


@register("sinewave")
class SineWaveSim(Sim):
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
    def __init__(self,
                 period_seconds: float = 1.0,
                 sample_wavelength: float = 10.0,
                 size: int = 50,
                 update_seconds: float = 1.0,
                 min_value: float = -5.0,
                 max_value: float = 5.0,
                 warning_percent: float = 80.0,
                 alarm_percent: float = 90.0):
        super(SineWaveSim, self).__init__(update_seconds)
        assert max_value > min_value, \
            "max_value %s is not > min_value %s" % (max_value, min_value)
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
                min_value, max_value, warning_percent, alarm_percent))
        self.channel.value = ArrayWrapper(np.zeros(size, dtype=np.float64))

    def compute_changes(self):
        t = time.time() - self.start
        x0 = t / self.period
        x = 2 * math.pi * (x0 + np.arange(self.size) / self.wavelength)
        value = ArrayWrapper(self.min + (np.sin(x) + 1.0) / 2.0 * self.range)
        return super(SineWaveSim, self).compute_changes(value=value)


class Wrapper:
    def __init__(self, arr):
        self.arr = arr

    @property
    def dtype(self):
        return self.arr.dtype

    def __eq__(self, other):
        return self.arr.__eq__(other)

    def __neq__(self, other):
        return self.arr.__neq__(other)



class SimPlugin(Plugin):
    def __init__(self):
        # {channel_id: Sim}
        self.sims: Dict[str, Sim] = {}
        # {channel_id: {queue_for_each_listener}}
        self.listeners: Dict[str, Set[Queue]] = {}

    async def _start_computing(self, channel_id: str):
        sim = self.sims[channel_id]
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
        del self.sims[channel_id]
        del self.listeners[channel_id]

    def _get_sim(self, channel_id: str) -> Sim:
        if channel_id not in self.sims:
            self.sims[channel_id] = make_sim_channel(channel_id)
            self.listeners[channel_id] = set()
            asyncio.create_task(self._start_computing(channel_id))
        return self.sims[channel_id]

    async def get_channel(self, channel_id: str, timeout: float) -> Channel:
        sim = self._get_sim(channel_id)
        return sim.channel

    async def subscribe_channel(self, channel_id: str):
        q = asyncio.Queue()
        try:
            sim = self._get_sim(channel_id)
            self.listeners[channel_id].add(q)
            yield sim.channel
            while True:
                yield await q.get()
        finally:
            self.listeners[channel_id].remove(q)
