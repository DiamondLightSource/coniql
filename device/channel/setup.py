import asyncio
import dataclasses
from typing import Dict, Any, List, Coroutine, Optional
from typing_extensions import Protocol, runtime_checkable
from functools import reduce

_TASKS = List[Coroutine]


@runtime_checkable
class CanSetup(Protocol):
    async def setup(self) -> None:
        raise NotImplementedError


async def setup(device_tree: Any):
    await asyncio.wait(gather_setup_tasks(device_tree))


def gather_setup_tasks(device_tree: Any,
                       tasks: Optional[_TASKS] = None) -> _TASKS:
    tasks = tasks or []
    if dataclasses.is_dataclass(device_tree):
        # Convert to dict for easier traversal
        return gather_setup_tasks(dataclasses.asdict(device_tree))
    elif isinstance(device_tree, CanSetup):
        # We have reached something with some setup logic
        return tasks + [device_tree.setup()]
    elif isinstance(device_tree, Dict):
        # No setup logic here, keep traversing
        child_tasks = [gather_setup_tasks(child)
                       for child in device_tree.values()]
        return tasks + reduce(lambda x, y: x + y, child_tasks)
