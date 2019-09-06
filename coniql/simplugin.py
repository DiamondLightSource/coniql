import math
from dataclasses import dataclass
from asyncio import Queue
from typing import Dict, List, Type

from .plugin import Plugin

CHANNEL_CLASSES: Dict[str, Type['SimChannel']] = {}


def register(func: str):
    def decorator(cls: Type[SimChannel]):
        CHANNEL_CLASSES[func] = cls
        return cls

    return decorator


def make_sim_channel(channel_id: str) -> 'SimChannel':
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
    return cls.from_parameters(*parameters)


class SimChannel:
    def __init__(self, update_seconds: float = 1.0):
        self.update_seconds = update_seconds
        self.channel = {}

    @classmethod
    def from_parameters(cls, *parameters: str) -> 'SimChannel':
        return cls(*parameters)


# TODO: duplication with schema, maybe graphene or attrs will help with this?

@dataclass
class NumberMeta:
    description: str
    tags: List[str]
    label: str
    array: bool


@register("sine")
class SineChannel:
    def __init__(self,
                 min_value: float = -5.0,
                 max_value: float = 5.0,
                 steps: float = 10.0,
                 update_seconds: float = 1.0,
                 warning_percent: float = 50.0,
                 alarm_percent: float = 75.0):
        super(SineChannel, self).__init__(update_seconds)
        assert max_value > min_value, \
            "max_value %s is not > min_value %s" % (max_value, min_value)
        self.min = min_value
        self.range = max_value - min_value
        alarm_range = self.range * alarm_percent / 100
        self.alarm_low = min_value + (self.range - alarm_range) / 2
        self.alarm_high = max_value - (self.range - alarm_range) / 2
        warning_range = self.range * warning_percent / 100
        self.warning_low = min_value + (self.range - warning_range) / 2
        self.warning_high = max_value - (self.range - warning_range) / 2
        self.step = 2 * math.pi / max(steps, 1)
        self.x = 0

    def compute(self):
        value = self.min + math.sin(self.x + 1.0) / 2.0 * self.range
        self.x += self.step
        return dict(value=value)


class SimPlugin(Plugin):
    def __init__(self):
        # {channel_id: Channel}
        self.channels: Dict[str, Dict] = {}
        # {channel_id: [queue_for_each_listener]}
        self.listeners: Dict[str, List[Queue]] = {}
