from enum import Enum

CS_AXIS_NAMES = list("ABCUVWXYZ")
MIN_TIME = 0.002
MIN_INTERVAL = 0.002


class CsAxis(Enum):
    A, B, C, U, V, W, X, Y, Z = CS_AXIS_NAMES
