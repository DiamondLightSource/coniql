import numpy as np

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional

from device.pmacutil.csaxismapping import CsAxisMapping


class VelocityMode(IntEnum):
    PREV_TO_NEXT = 0
    PREV_TO_CURRENT = 1
    CURRENT_TO_NEXT = 2
    ZERO_VELOCITY = 3


# user programs
class UserProgram(IntEnum):
    NO_PROGRAM = 0  # Do nothing
    LIVE_PROGRAM = 1  # GPIO123 = 1, 0, 0
    DEAD_PROGRAM = 2  # GPIO123 = 0, 1, 0
    MID_PROGRAM = 4  # GPIO123 = 0, 0, 1
    ZERO_PROGRAM = 8  # GPIO123 = 0, 0, 0


class PointType(IntEnum):
    START_OF_ROW = 0  # Lower bound of first point of row
    MID_POINT = 1  # Position of any point
    POINT_JOIN = 2  # Boundary of two joined points
    END_OF_ROW = 3  # Upper boundary of last point of row
    TURNAROUND = 4  # Between rows


@dataclass
class PmacTrajectoryProfile:
    time_array: List[float]
    user_programs: Optional[List[int]] = None
    velocity_mode: Optional[List[float]] = None
    axes: CsAxisMapping[List[float]] = CsAxisMapping(
        [], [], [], [], [], [], [], [], [])

    @classmethod
    def empty(cls):
        return PmacTrajectoryProfile([], [], [])

    def __getitem__(self, item):
        return self.axes.__getitem__(item)
