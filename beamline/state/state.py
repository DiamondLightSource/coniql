from dataclasses import dataclass
from typing import TypeVar, Generic, List, Any, Callable, Optional, Dict

from device.devices.positioner import Positioner
from device.devicetypes.channel import ReadableChannel
from device.inmemory.channel import InMemoryReadOnlyChannel, \
    InMemoryReadWriteChannel

T = TypeVar('T')

PositionerConstraint = Callable[[Positioner], float]
PositionerConstraints = Dict[Positioner, PositionerConstraint]


def pos(current_pos=0.0):
    return Positioner(
        position=InMemoryReadOnlyChannel(current_pos),
        setpoint=InMemoryReadWriteChannel(current_pos)
    )


motor_x = pos()
motor_y = pos()

motor_x_demand = 4.2
motor_y_demand = -2.1

def xy_constraint() -> bool:
    pass


class PositionerSolver:
    def __init__(self, default_constraints: Optional[PositionerConstraints] = None):
        self.default_constraints = default_constraints or {}

    def solve(self, constraints: PositionerConstraints):
        all_constraints = {*self.default_constraints, *constraints}
        for positioner, constraint in all_constraints.items():
            positioner.