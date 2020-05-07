import asyncio
import math
import time
from asyncio import Queue
from typing import Any, AsyncGenerator, Dict, Set, Type

import numpy as np

from coniql.plugin import Plugin
from coniql.types import (
    Channel,
    ChannelDisplay,
    ChannelStatus,
    ChannelTime,
    ChannelValue,
    Range,
)

# How long to keep Sim alive after the last listener has gone
SIM_DESTROY_TIMEOUT = 10

# Map of channel_id func to its Sim class
CHANNEL_CLASSES: Dict[str, Type["SimChannel"]] = {}


def register_channel(func: str):
    def decorator(cls: Type[SimChannel]):
        CHANNEL_CLASSES[func] = cls
        return cls

    return decorator


class SimChannel:
    def __init__(
        self, id: str, update_seconds: float,
    ):
        self.update_seconds = update_seconds
        self.channel = Channel(
            id, time=ChannelTime.now(), status=ChannelStatus.valid(),
        )

    def apply_changes(self, value, **changes: Any) -> Dict[str, Any]:
        for k, v in list(changes.items()):
            # pop changes that are actually the same
            if v == getattr(self.channel, k):
                changes.pop(k)
        # value needs special treatment as might wrap a numpy array
        assert self.channel.value is not None, self.channel
        value_changed = value != self.channel.value.value
        if hasattr(value_changed, "any"):
            value_changed = value_changed.any()
        if value_changed:
            changes["value"] = ChannelValue(value, self.channel.value.formatter)
        changes["time"] = ChannelTime.now()
        for k, v in changes.items():
            setattr(self.channel, k, v)
        changes["id"] = self.channel.id
        return changes

    def compute_changes(self):
        raise NotImplementedError(self)


def make_display(
    min_value: float,
    max_value: float,
    warning_percent: float,
    alarm_percent: float,
    label: str,
    description: str,
    role: str,
    widget: str,
) -> ChannelDisplay:
    assert max_value > min_value, "max_value %s is not > min_value %s" % (
        max_value,
        min_value,
    )
    display_range = max_value - min_value
    alarm_range = display_range * alarm_percent / 100
    warning_range = display_range * warning_percent / 100
    display = ChannelDisplay(
        label=label,
        description=description,
        role=role,
        widget=widget,
        controlRange=Range(min_value, max_value),
        displayRange=Range(min_value, max_value),
        alarmRange=Range(
            min_value + (display_range - alarm_range) / 2,
            max_value - (display_range - alarm_range) / 2,
        ),
        warningRange=Range(
            min_value + (display_range - warning_range) / 2,
            max_value - (display_range - warning_range) / 2,
        ),
        units="au",
        precision=5,
        form="DEFAULT",
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
        id: str,
        min_value: float = -5.0,
        max_value: float = 5.0,
        steps: float = 10.0,
        update_seconds: float = 1.0,
        warning_percent: float = 80.0,
        alarm_percent: float = 90.0,
    ):
        super().__init__(id, update_seconds)
        self.min = min_value
        self.range = max_value - min_value
        self.step = 2 * math.pi / max(steps, 1)
        self.x = 0
        self.channel.display = make_display(
            min_value,
            max_value,
            warning_percent,
            alarm_percent,
            label="Sine Value",
            description="A Sine value generator",
            role="RO",
            widget="TEXTUPDATE",
        )
        self.channel.value = ChannelValue(
            0, self.channel.display.make_number_formatter()
        )

    def compute_changes(self):
        self.x += self.step
        value = self.min + (math.sin(self.x) + 1.0) / 2.0 * self.range
        if not self.channel.display.alarmRange.contains(value):
            status = ChannelStatus.alarm("Outside alarm range")
        elif not self.channel.display.warningRange.contains(value):
            status = ChannelStatus.warning("Outside warning range")
        else:
            status = ChannelStatus.valid()
        return self.apply_changes(value, status=status)


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
        id: str,
        period_seconds: float = 1.0,
        sample_wavelength: float = 10.0,
        size: int = 50,
        update_seconds: float = 1.0,
        min_value: float = -5.0,
        max_value: float = 5.0,
        warning_percent: float = 80.0,
        alarm_percent: float = 90.0,
    ):
        super().__init__(id, update_seconds)
        self.min = min_value
        self.range = max_value - min_value
        self.period = max(period_seconds, 0.001)
        self.size = size
        self.wavelength = sample_wavelength
        self.start = time.time()
        self.channel.display = make_display(
            min_value,
            max_value,
            warning_percent,
            alarm_percent,
            label="Sine Waveform",
            description="A Sine waveform generator",
            role="RO",
            widget="PLOT",
        )
        self.channel.value = ChannelValue(
            np.zeros(size, dtype=np.float64),
            self.channel.display.make_ndarray_formatter(),
        )

    def compute_changes(self):
        t = time.time() - self.start
        x0 = t / self.period
        x = 2 * math.pi * (x0 + np.arange(self.size) / self.wavelength)
        value = self.min + (np.sin(x) + 1.0) / 2.0 * self.range
        return self.apply_changes(value)


class SimPlugin(Plugin):
    def __init__(self):
        # {channel_id: SimChannel}
        self.sim_channels: Dict[str, SimChannel] = {}
        # {channel_id: {queue_for_each_listener}}
        self.listeners: Dict[str, Set[Queue]] = {}

    async def _start_computing(self, channel_id: str):
        sim = self.sim_channels[channel_id]
        next_compute = time.time()
        last_had_listeners = next_compute
        while next_compute - last_had_listeners < SIM_DESTROY_TIMEOUT:
            next_compute += sim.update_seconds
            await asyncio.sleep(next_compute - time.time())
            changes = sim.compute_changes()
            for q in self.listeners[channel_id]:
                last_had_listeners = next_compute
                await q.put(changes)
        # no-one listening, remove sim
        del self.sim_channels[channel_id]
        del self.listeners[channel_id]

    async def get_channel(self, channel_id: str, timeout: float = 0) -> Channel:
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
            self.sim_channels[channel_id] = cls(
                f"{self.name}://{channel_id}", *parameters
            )
            self.listeners[channel_id] = set()
            asyncio.create_task(self._start_computing(channel_id))
        return self.sim_channels[channel_id].channel

    async def subscribe_channel(self, channel_id: str) -> AsyncGenerator[Channel, None]:
        q: Queue[Channel] = asyncio.Queue()
        try:
            channel = await self.get_channel(channel_id)
            self.listeners[channel_id].add(q)
            yield channel
            while True:
                yield await q.get()
        finally:
            self.listeners[channel_id].remove(q)

    async def put_channel(self, channel_id, value, timeout):
        raise RuntimeError(
            f"Cannot put {value!r} to {self.name}://{channel_id}, as it isn't writeable"
        )
