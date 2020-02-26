from dataclasses import dataclass
from typing import TypeVar, Generic

from device.pmacutil.pmacconst import CS_AXIS_NAMES

T = TypeVar('T')


@dataclass
class CsAxisMapping(Generic[T]):
    a: T
    b: T
    c: T
    u: T
    v: T
    w: T
    x: T
    y: T
    z: T

    def __getitem__(self, item: str):
        # TODO: Should be case sensitive
        item = item.lower()
        names = [c.lower() for c in CS_AXIS_NAMES]
        if item in names:
            return self.__dict__[item]
        else:
            raise KeyError(f'{item} not a valid CS axis')