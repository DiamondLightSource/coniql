from enum import Enum, IntEnum

CS_AXIS_NAMES = list("ABCUVWXYZ")
MIN_TIME = 0.002
MIN_INTERVAL = 0.002


class CsAxis(Enum):
    A, B, C, U, V, W, X, Y, Z = CS_AXIS_NAMES


class VelocityMode(IntEnum):
    PREV_TO_NEXT = 0
    PREV_TO_CURRENT = 1
    CURRENT_TO_NEXT = 2
    ZERO_VELOCITY = 3


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