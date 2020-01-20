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


def xy_constraint(demands) -> bool:
    motor_x_demand, motor_y_demand = demands
    return motor_x_demand > motor_y_demand or motor_x_demand + motor_y_demand < 5.0


def x_constraint(demands) -> bool:
    motor_x_demand, _ = demands
    return motor_x_demand - int(motor_x_demand) < 0.5


def positive_constraint(demands) -> bool:
    motor_x_demand, motor_y_demand = demands
    return motor_x_demand > 0.0 and motor_y_demand > 0.0


class PositionerSolver:
    def __init__(self, constraints=None, conc_constraints=None):
        self.constraints = constraints or []
        self.conc_constraints = conc_constraints or []

    def sat(self, demands):
        for demand in demands:
            for constraint in self.constraints:
                if not constraint(demands):
                    return False
        return True

    def solve(self, demands):
        if not self.sat(demands):
            return 'Not sat!'
        else:
            for demand in demands:
                pass


solver = PositionerSolver([positive_constraint, x_constraint, xy_constraint])

a = solver.solve((5.0, 4.0))
print(a)
