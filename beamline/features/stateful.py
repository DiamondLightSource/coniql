from dataclasses import dataclass
from typing import List


class StatefulBeamline:
    """A beamline implementing this trait can move to a specified state using
    abstract devices"""
    async def move_to_state(self, state):
        return NotImplemented

