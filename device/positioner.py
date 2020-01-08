from dataclasses import dataclass


@dataclass
class Positioner:
    """Abstract representation of a device that minimises error between a
    setpoint and an indicated position e.g. a motor or temperature controller"""
    pass
