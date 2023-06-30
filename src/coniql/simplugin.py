import asyncio
import math
import time
from dataclasses import dataclass, replace
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence, Set, Type

import numpy as np

from coniql.coniql_schema import DisplayForm, Widget
from coniql.plugin import Plugin, PutValue
from coniql.types import (
    Channel,
    ChannelDisplay,
    ChannelFormatter,
    ChannelRole,
    ChannelStatus,
    ChannelTime,
    ChannelValue,
    Range,
)

# How long to keep Sim alive after the last listener has gone
SIM_DESTROY_TIMEOUT = 10

# Map of pv func to its Sim class
CHANNEL_CLASSES: Dict[str, Type["Sim"]] = {}


def register_channel(func: str):
    def decorator(cls: Type[Sim]):
        CHANNEL_CLASSES[func] = cls
        return cls

    return decorator


@dataclass
class SimChannel(Channel):
    id: Optional[str] = None
    value: Optional[ChannelValue] = None
    display: Optional[ChannelDisplay] = None
    time: Optional[ChannelTime] = None
    status: Optional[ChannelStatus] = None

    def get_id(self) -> Optional[str]:
        return self.id

    def get_value(self) -> Optional[ChannelValue]:
        return self.value

    def get_display(self) -> Optional[ChannelDisplay]:
        return self.display

    def get_time(self) -> Optional[ChannelTime]:
        return self.time

    def get_status(self) -> Optional[ChannelStatus]:
        return self.status


class Sim:
    def __init__(self, update_seconds: float):
        self.update_seconds = update_seconds
        self.channel = SimChannel(time=ChannelTime.now(), status=ChannelStatus.valid())

    def apply_changes(self, value, **changes) -> Channel:
        # pop changes that haven't really changed
        changes = {k: v for k, v in changes.items() if getattr(self.channel, k) != v}
        # value needs special treatment as might wrap a numpy array
        assert self.channel.value is not None, self.channel
        # Don't check numpy arrays as it's expensive, assume it changed
        if isinstance(value, np.ndarray) or value != self.channel.value.value:
            changes["value"] = ChannelValue(value, self.channel.value.formatter)
        # time always changes
        changes["time"] = ChannelTime.now()
        # replace our stored channel with an updated one
        self.channel = replace(self.channel, **changes)
        # a channel with our differences
        channel = SimChannel(**changes)
        return channel

    def compute_changes(self) -> Channel:
        raise NotImplementedError(self)


def make_display(
    min_value: float,
    max_value: float,
    warning_percent: float,
    alarm_percent: float,
    description: str,
    role: ChannelRole,
    widget: Widget,
) -> ChannelDisplay:
    assert max_value > min_value, "max_value %s is not > min_value %s" % (
        max_value,
        min_value,
    )
    display_range = max_value - min_value
    alarm_range = display_range * alarm_percent / 100
    warning_range = display_range * warning_percent / 100
    display = ChannelDisplay(
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
        form=DisplayForm.DEFAULT,
    )
    return display


@register_channel("sine")
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

    def __init__(
        self,
        min_value: float = -5.0,
        max_value: float = 5.0,
        steps: float = 10.0,
        update_seconds: float = 1.0,
        warning_percent: float = 80.0,
        alarm_percent: float = 90.0,
    ):
        super().__init__(update_seconds)
        self.min = min_value
        self.range = max_value - min_value
        self.step = 2 * math.pi / max(steps, 1)
        self.x = 0.0
        display = make_display(
            min_value,
            max_value,
            warning_percent,
            alarm_percent,
            description="A Sine value generator",
            role=ChannelRole.RO,
            widget=Widget.TEXTUPDATE,
        )
        self.channel.display = display
        self.channel.value = ChannelValue(
            0,
            ChannelFormatter.for_number(display.precision, display.units),
        )

    def compute_changes(self):
        self.x += self.step
        value = self.min + (math.sin(self.x) + 1.0) / 2.0 * self.range
        assert self.channel.display is not None
        assert self.channel.display.alarmRange is not None
        assert self.channel.display.warningRange is not None
        if not self.channel.display.alarmRange.contains(value):
            status = ChannelStatus.alarm("Outside alarm range")
        elif not self.channel.display.warningRange.contains(value):
            status = ChannelStatus.warning("Outside warning range")
        else:
            status = ChannelStatus.valid()
        return self.apply_changes(value, status=status)


@register_channel("sinewave")
class SineWaveSim(Sim):
    """Create a simulated float waveform of a sine wave

    Args:
        period_seconds: The time between repetitions on the sinewave in time
        sample_wavelength: The wavelength of the output sinewave
        size: The size of the output waveform (min 10 elements)
        update_seconds: The time between each step
        min_value: The minimum output value
        max_value: The maximum output value
    """

    def __init__(
        self,
        period_seconds: float = 1.0,
        sample_wavelength: float = 10.0,
        size: float = 50.0,
        update_seconds: float = 1.0,
        min_value: float = -5.0,
        max_value: float = 5.0,
    ):
        super().__init__(update_seconds)
        self.min = min_value
        self.range = max_value - min_value
        self.period = max(period_seconds, 0.001)
        self.size = int(size)
        self.wavelength = sample_wavelength
        self.start = time.time()
        display = make_display(
            min_value,
            max_value,
            warning_percent=100.0,
            alarm_percent=100.0,
            description="A Sine waveform generator",
            role=ChannelRole.RO,
            widget=Widget.PLOTY,
        )
        self.channel.display = display
        self.channel.value = ChannelValue(
            np.zeros(self.size, dtype=np.float64),
            ChannelFormatter.for_ndarray(display.precision, display.units),
        )

    def compute_changes(self) -> Channel:
        t = time.time() - self.start
        x0 = t / self.period
        x = 2 * math.pi * (x0 + np.arange(self.size) / self.wavelength)
        value = self.min + (np.sin(x) + 1.0) / 2.0 * self.range
        return self.apply_changes(value)


@register_channel("rampwave")
class RampWaveSim(Sim):
    """Create a simulated float waveform of a ramping variable

    Args:
        size: The size of the output waveform
        update_seconds: The time between new waveform updates
        min_value: The minimum output value (inclusive)
        max_value: The maximum output value (exclusive)
        step: The step between each value in the ramp
    """

    def __init__(
        self,
        size: float = 10.0,
        update_seconds: float = 1.0,
        min_value: float = 0.0,
        max_value: float = 100.0,
        step: float = 1.0,
    ):
        super().__init__(update_seconds)
        self.size = int(size)
        # A single ramp waveform
        ramp = np.arange(min_value, max_value, step)
        self.ramp_length = len(ramp)
        # How many of these ramps in a single output waveform
        iterations = math.ceil(self.size / self.ramp_length)
        # Output waveform that we will take sliding slices out of
        self.ramps = np.tile(ramp, iterations + 1)
        self.i = 0

        display = make_display(
            min_value,
            max_value,
            warning_percent=100.0,
            alarm_percent=100.0,
            description="A ramp waveform generator",
            role=ChannelRole.RO,
            widget=Widget.PLOTY,
        )
        self.channel.display = display
        self.channel.value = ChannelValue(
            self.ramps[: self.size],
            ChannelFormatter.for_ndarray(display.precision, display.units),
        )

    def compute_changes(self) -> Channel:
        self.i += 1
        if self.i >= self.ramp_length:
            self.i = 0
        value = self.ramps[self.i : self.i + self.size]
        return self.apply_changes(value)


class SimPlugin(Plugin):
    def __init__(self) -> None:
        # {pv: Sim}
        self.sims: Dict[str, Sim] = {}
        # {pv: {queue_for_each_listener}}
        self.listeners: Dict[str, Set[asyncio.Queue[Channel]]] = {}
        # Set of asyncio tasks running
        self.task_references: Set[asyncio.Task[Any]] = set()

    async def _start_computing(self, pv: str):
        sim = self.sims[pv]
        next_compute = time.time()
        last_had_listeners = next_compute
        while next_compute - last_had_listeners < SIM_DESTROY_TIMEOUT:
            next_compute += sim.update_seconds
            await asyncio.sleep(next_compute - time.time())
            changes = sim.compute_changes()
            for q in self.listeners[pv]:
                last_had_listeners = next_compute
                await q.put(changes)
        # no-one listening, remove sim
        del self.sims[pv]
        del self.listeners[pv]

    async def get_channel(self, pv: str, timeout: float) -> Channel:
        if pv not in self.sims:
            if "(" in pv:
                assert pv.endswith(")"), "Missing closing bracket in %r" % pv
                func, param_str = pv[:-1].split("(", 1)
                parameters = [float(param.strip()) for param in param_str.split(",")]
            else:
                func = pv
                parameters = []
            cls = CHANNEL_CLASSES[func]
            inst = cls(*parameters)
            display = inst.channel.display
            assert display
            self.sims[pv] = inst
            self.listeners[pv] = set()
            task = asyncio.create_task(self._start_computing(pv))
            self.task_references.add(task)

            def _on_completion(t):
                self.task_references.remove(t)

            task.add_done_callback(_on_completion)

        return self.sims[pv].channel

    async def subscribe_channel(self, pv: str) -> AsyncGenerator[Channel, None]:
        q: asyncio.Queue[Channel] = asyncio.Queue()
        try:
            channel = await self.get_channel(pv, 0)
            self.listeners[pv].add(q)
            yield channel
            while True:
                yield await q.get()
        finally:
            self.listeners[pv].remove(q)

    async def put_channels(
        self, pvs: List[str], values: Sequence[PutValue], timeout: float
    ):
        raise RuntimeError(f"Cannot put {values!r} to {pvs}, as they aren't writeable")
