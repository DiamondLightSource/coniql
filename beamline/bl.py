import numpy as np
import asyncio

from typing import Tuple, List
from dataclasses import dataclass

from beamline.scheme.scheme import Scheme, ArmedScheme
from device.devices.camera import Camera
from device.devices.faketriggerbox import FakeTriggerBox
from device.devices.stage3d import Stage3D


def exposure_delay(exposure_time: float, acquire_period: float) -> float:
    readout_time = acquire_period - exposure_time
    return readout_time / 2


@dataclass
class AdSimTriggeringScheme:
    trigger_box: FakeTriggerBox
    main_detector: Camera
    secondary_detector: Camera
    sample_stage: Stage3D


@dataclass
class AdSimTriggeringSchemePre(AdSimTriggeringScheme, Scheme):
    async def prepare(self) -> ArmedScheme:
        await self.trigger_box.min_seconds_between_checks.put(0.01)
        readout = self.sample_stage.x.position
        trigger = self.main_detector.acquire
        await self.trigger_box.trigger_1.input.put(readout)
        await self.trigger_box.trigger_1.output.put(trigger)

        exposure_time = await self.main_detector.exposure_time.get()
        acquire_period = await self.main_detector.acquire_period.get()
        delay = exposure_delay(exposure_time.value, acquire_period.value)
        await self.trigger_box.trigger_1.delay_seconds.put(delay)


