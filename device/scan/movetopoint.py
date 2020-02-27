import asyncio
from typing import Iterable

from typing_extensions import Protocol
from scanpointgenerator import Point

from device.channel.channeltypes.channel import ReadWriteChannel


class Scannable(Protocol):
    scannable_name: ReadWriteChannel[str]
    setpoint: ReadWriteChannel[float]


async def move_to_point(scannables: Iterable[Scannable], point: Point):
    jobs = []
    for scannable in scannables:
        name = await scannable.scannable_name.get()
        if name in point.positions:
            pos = point.positions[name]
            jobs.append(scannable.setpoint.put(pos))
    return await asyncio.wait(jobs)
