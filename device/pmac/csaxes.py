from dataclasses import dataclass
from typing import TypeVar, Generic, Iterable
from typing_extensions import Protocol

from device.pmac.modes import CS_AXIS_NAMES

T = TypeVar('T')


class CsAxes(Protocol[T]):
    a: T
    b: T
    c: T
    u: T
    v: T
    w: T
    x: T
    y: T
    z: T


def get_axis(axes: CsAxes, item: str) -> T:
    # TODO: Should be case sensitive
    item = item.lower()
    names = [c.lower() for c in CS_AXIS_NAMES]
    if item in names:
        return axes.__dict__[item]
    else:
        raise KeyError(f'{item} not a valid CS axis')


def iterator(axes: CsAxes) -> Iterable[T]:
    return [axes.a, axes.b, axes.c, axes.u, axes.v, axes.w, axes.x,
            axes.y, axes.z]
