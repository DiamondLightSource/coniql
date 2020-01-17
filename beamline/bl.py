import numpy as np
import asyncio

from typing import Tuple, List
from dataclasses import dataclass

from beamline.mock.mx import MockMxBeamline
from device.devices.goniometer import Goniometer


@dataclass
class RotationScan:
    omega_range: Tuple[float, float]
    chi: float
    phi: float
    velocity: float


@dataclass
class MxExperimentModel:
    scans: List[RotationScan]


beamline = MockMxBeamline()


async def run(experiment_model: MxExperimentModel):
    for scan in experiment_model.scans:
        await beamline.rotation_scan(scan)


expt = MxExperimentModel([
    RotationScan((0.0, 10.0), 0.0, 0.0, 1.0),
    RotationScan((2.0, 3.0), 0.0, 0.0, 0.1),
])

asyncio.run(run(expt))
