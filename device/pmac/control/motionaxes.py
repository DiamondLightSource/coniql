from collections import Counter
from typing import List, Sequence, Dict

from scanpointgenerator import CompoundGenerator, StaticPointGenerator

from device.pmac.modes import CS_AXIS_NAMES
from device.pmac.motorinfo import MotorInfo, motor_info
from device.pmac.protocol.motor import PmacMotor


async def cs_port_with_motors_in(motors: List[PmacMotor]) -> str:
    for motor in motors:
        cs = await motor.cs()
        if cs.axis in CS_AXIS_NAMES:
            return cs.port
    raise ValueError("Can't find a cs port to use in %s" % motors)


def get_motion_axes(generator: CompoundGenerator) -> List[str]:
    """Filter axes_to_move to only contain motion axes"""
    axes: List[str] = []
    for subgenerator in generator.generators:
        if not isinstance(subgenerator, StaticPointGenerator):
            axes += subgenerator.axes
    return axes


async def cs_axis_mapping(motors: List[PmacMotor],
                          axes_to_move: Sequence[str]) -> Dict[str, MotorInfo]:
    """Given the layout table of a PMAC, create a MotorInfo for every axis in
    axes_to_move that isn't generated by a StaticPointGenerator. Check that they
    are all in the same CS"""
    cs_ports = set()  # type: Set[str]
    axis_mapping = {}  # type: Dict[str, MotorInfo]

    for motor in motors:
        cs = await motor.cs()
        name = await motor.scannable_name.get()
        if name in axes_to_move:
            cs_ports.add(cs.port)
            axis_mapping[name] = await motor_info(cs, name, motor)

    missing = list(set(axes_to_move) - set(axis_mapping))
    assert not missing, \
        "Some scannables %s are not in the CS mapping %s" % (
            missing, axis_mapping)
    assert len(cs_ports) == 1, \
        "Requested axes %s are in multiple CS numbers %s" % (
            axes_to_move, list(cs_ports))
    cs_axis_counts = Counter([x.cs.axis for x in axis_mapping.values()])
    # Any cs_axis defs that are used for more that one raw motor
    overlap = [k for k, v in cs_axis_counts.items() if v > 1]
    assert not overlap, \
        "CS axis defs %s have more that one raw motor attached" % overlap
    return axis_mapping