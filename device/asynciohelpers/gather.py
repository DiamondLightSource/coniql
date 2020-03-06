import asyncio
from typing import Dict, Any, Coroutine


async def asyncio_gather_values(coros: Dict[Any, Coroutine[Any, Any, Any]]) -> \
        Dict[Any, Any]:
    ts = [wrap_coro(key, coro)() for key, coro in coros.items()]
    rs = await asyncio.gather(*ts)
    return {
        k: v for k, v in rs
    }


def wrap_coro(meta, coro):
    async def wrapper():
        coro_result = await coro
        return meta, coro_result

    return wrapper