import asyncio
from dataclasses import is_dataclass
from pprint import pprint
from typing import Dict, Any, List, Coroutine

from device.channel.channeltypes.channel import ReadableChannel, WriteableChannel
from coniql.asynciohelpers import asyncio_gather_values

_DESIGN = Dict[str, Any]


async def snapshot(device) -> _DESIGN:
    return await asyncio_gather_values({
        name: value(fld)
        for name, fld in device.__dict__.items()
    })


# TODO: Block read only channels at type level
async def value(fld: Any):
    if is_dataclass(fld):
        return await snapshot(fld)
    elif isinstance(fld, ReadableChannel):
        return (await fld.get()).value
    else:
        raise KeyError(f'Unable to snapshot {fld}')


async def restore(design: _DESIGN, device) -> Coroutine:
    tasks = restore_tasks(design, device)
    pprint(tasks)
    return await asyncio.gather(*tasks)


def restore_tasks(design: _DESIGN, device) -> List[Coroutine]:
    tasks = []
    for field_name, val in design.items():
        print(f'Restoring {field_name}')
        fld = device.__dict__[field_name]
        if is_dataclass(fld):
            tasks = tasks + restore_tasks(val, fld)
        elif isinstance(fld, WriteableChannel):
            tasks.append(fld.put(val))
        else:
            raise KeyError(f'Immutable channel {field_name}')
    return tasks
